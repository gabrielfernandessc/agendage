from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

app = Flask(__name__)
CORS(app)

def get_ge_data(date):
    """Obtém o HTML da página do GE para a data especificada."""
    try:
        print(f"Fetching HTML for date: {date}")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        url = f'https://ge.globo.com/agenda/#/futebol/{date}'
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'eventGrouperstyle__GroupByChampionshipsWrapper-sc-1bz1qr-0')))
        time.sleep(5)
        html = driver.page_source
        print("HTML fetched successfully")
        driver.quit()
        return html
    except Exception as e:
        print(f"Error fetching HTML: {str(e)}")
        raise Exception(f'Erro ao acessar GE.globo: {str(e)}')

def parse_games(html, date):
    """Parseia o HTML e retorna uma lista de jogos de futebol formatados."""
    dia, mes, ano = date.split('-')
    data_formatada = f'{dia}/{mes}/{ano}'

    soup = BeautifulSoup(html, 'html.parser')
    games = []

    championship_groups = soup.find_all('div', class_='eventGrouperstyle__GroupByChampionshipsWrapper-sc-1bz1qr-0')
    print(f"Found {len(championship_groups)} championship groups")

    for group in championship_groups:
        champ_name = group.find('span', class_='eventGrouperstyle__ChampionshipName-sc-1bz1qr-2')
        if not champ_name:
            continue
        championship = champ_name.text.strip()
        print(f"Processing championship: {championship}")

        game_cards = group.find_all('a', class_='sc-eldPxv')
        print(f"Found {len(game_cards)} games in {championship}")

        for card in game_cards:
            try:
                spans = card.find_all('span', class_='sc-jXbUNg')
                if len(spans) < 2:
                    continue
                time = None
                for span in spans[::-1]:
                    text = span.text.strip()
                    if any(char.isdigit() for char in text) and ':' in text:
                        time = text
                        break
                if not time:
                    continue

                teams = card.find_all('span', class_='sc-eeDRCY')
                if len(teams) < 2:
                    continue
                home = teams[0].text.strip()
                away = teams[1].text.strip()

                jogo_formatado = f'{data_formatada} - {time} - {home} x {away}'
                games.append({
                    'campeonato': championship,
                    'jogo_formatado': jogo_formatado
                })
            except Exception as e:
                print(f'Erro ao parsear jogo: {str(e)}')
                continue

    if not games:
        print("Nenhum jogo encontrado. Verifique se o HTML mudou.")
    else:
        print(f"Total de {len(games)} jogos encontrados.")

    games.sort(key=lambda x: (x['campeonato'], x['jogo_formatado']))
    return games

@app.route('/get-jogos/<date>')
def get_jogos(date):
    """Rota para retornar os jogos do dia especificado."""
    try:
        html = get_ge_data(date)
        jogos = parse_games(html, date)
        if not jogos:
            return jsonify({'error': 'Nenhum jogo encontrado'}), 404
        return jsonify(jogos)
    except Exception as e:
        print(f"Error in /get-jogos/{date}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/gerar-pdf/<date>', methods=['POST'])
def gerar_pdf(date):
    """Rota para gerar um PDF dos jogos enviados pelo frontend."""
    try:
        print(f"Generating PDF for date: {date}")
        data = request.get_json()
        jogos = data.get('jogos', [])
        
        if not jogos:
            return jsonify({'error': 'Nenhum jogo fornecido para gerar o PDF'}), 400

        # Criar o PDF em memória com reportlab
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Título
        story.append(Paragraph(f"Agenda de Jogos - {date}", styles['Title']))
        story.append(Spacer(1, 12))

        # Adicionar campeonatos e jogos
        for item in jogos:
            campeonato = item['campeonato']
            story.append(Paragraph(campeonato, styles['Heading2']))
            for jogo in item['jogos']:
                story.append(Paragraph(jogo, styles['BodyText']))
            story.append(Spacer(1, 12))

        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()

        print("PDF generated successfully with reportlab")
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'agenda_ge_{date}.pdf'
        )
    except Exception as e:
        print(f"Error generating PDF for {date}: {str(e)}")
        return jsonify({'error': f'Erro ao gerar PDF: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)