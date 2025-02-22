from flask import Flask, request, send_file, render_template_string
import pdfkit
import os

app = Flask(__name__)

# Carregar o index.html como string
with open("index.html", "r", encoding="utf-8") as f:
    INDEX_HTML = f.read()

@app.route('/')
def home():
    return render_template_string(INDEX_HTML)

@app.route('/get-jogos/<data>', methods=['GET'])
def get_jogos(data):
    # Mock de jogos para teste (substitua por lógica real se desejar)
    jogos = [
        {"campeonato": "Brasileirão", "jogo_formatado": f"Flamengo x Corinthians - {data} 16:00"},
        {"campeonato": "Brasileirão", "jogo_formatado": f"Palmeiras x São Paulo - {data} 19:00"},
        {"campeonato": "Copa do Brasil", "jogo_formatado": f"Grêmio x Internacional - {data} 21:00"}
    ]
    return jogos

@app.route('/gerar-pdf/<data>', methods=['POST'])
def gerar_pdf(data):
    data_json = request.json
    jogos = data_json.get('jogos', [])

    if not jogos:
        return {"error": "Nenhum jogo fornecido"}, 400

    # Gerar HTML para o PDF
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            h2 {{ color: #3498db; }}
            p {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <h1>Agenda de Jogos - {data}</h1>
    """
    for campeonato in jogos:
        html_content += f"<h2>{campeonato['campeonato']}</h2>"
        for jogo in campeonato['jogos']:
            html_content += f"<p>{jogo}</p>"
    html_content += "</body></html>"

    options = {
        'page-size': 'A4',
        'encoding': "UTF-8",
        'enable-local-file-access': None
    }

    pdf_file = "output.pdf"
    pdfkit.from_string(html_content, pdf_file, options=options)

    return send_file(pdf_file, as_attachment=True, download_name=f"agenda_ge_{data}.pdf")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)