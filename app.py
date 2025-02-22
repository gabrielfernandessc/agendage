from flask import Flask, jsonify, send_file, request, send_from_directory
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
import os

app = Flask(__name__)
CORS(app)

def setup_chrome():
    """Configura o ChromeDriver para rodar em modo headless."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--single-process')
    return options

def get_ge_data(date):
    """Obtém o HTML da página do GE para a data especificada."""
    try:
        print(f"Fetching HTML for date: {date}")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=setup_chrome()
        )
        url = f'https://ge.globo.com/agenda/#/futebol/{date}'
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'eventGrouperstyle__GroupByChampionshipsWrapper-sc-1bz1qr-0'))
        )
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
    try:
        # Validação da data
        if not date or len(date.split('-')) != 3:
            raise ValueError("Formato de data inválido")

        dia, mes, ano = date.split('-')
        data_formatada = f'{dia}/{mes}/{ano}'

        soup = BeautifulSoup(html, 'html.parser')
        games = []

        # Verifica se o HTML contém os elementos esperados
        championship_groups = soup.find_all('div', class_='eventGrouperstyle__GroupByChampionshipsWrapper-sc-1bz1qr-0')
        if not championship_groups:
            print("Nenhum grupo de campeonatos encontrado no HTML.")
            return games

        for group in championship_groups:
            # Extração mais segura do nome do campeonato
            champ_name = group.find('span', class_='eventGrouperstyle__ChampionshipName-sc-1bz1qr-2')
            if not champ_name:
                print("Nome do campeonato não encontrado.")
                continue
                
            championship = champ_name.get_text(strip=True)
            if not championship:
                print("Nome do campeonato vazio.")
                continue

            game_cards = group.find_all('a', class_='sc-eldPxv')
            if not game_cards:
                print(f"Nenhum jogo encontrado para o campeonato: {championship}")
                continue
            
            for card in game_cards:
                try:
                    # Extração mais robusta do horário
                    time_element = card.find('span', class_='sc-jXbUNg')
                    if not time_element:
                        print("Horário não encontrado.")
                        continue
                        
                    time = time_element.get_text(strip=True)
                    if not any(char.isdigit() for char in time):
                        print(f"Horário inválido: {time}")
                        continue

                    # Extração dos times
                    teams = card.find_all('span', class_='sc-eeDRCY')
                    if len(teams) < 2:
                        print("Times não encontrados.")
                        continue
                        
                    home = teams[0].get_text(strip=True)
                    away = teams[1].get_text(strip=True)

                    games.append({
                        'campeonato': championship,
                        'jogo_formatado': f'{data_formatada} - {time} - {home} x {away}'
                    })
                    
                except Exception as e:
                    print(f'Erro ao parsear card: {str(e)}')
                    continue

        games.sort(key=lambda x: (x['campeonato'], x['jogo_formatado']))
        return games

    except Exception as e:
        print(f'Erro no parse_games: {str(e)}')
        raise

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

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Agenda de Jogos - {date}", styles['Title']))
        story.append(Spacer(1, 12))

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

@app.route('/')
def index():
    """Rota principal para servir o arquivo index.html."""
    return send_file('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Rota para servir arquivos estáticos."""
    return send_from_directory('static', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
