import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import schedule
import time
import os

# --- CONFIGURAÇÕES ---
TOKEN = ''
CHAT_ID = ''
bot = telebot.TeleBot(TOKEN)

DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_MEMORIA = os.path.join(DIRETORIO_SCRIPT, "ofertas_enviadas.txt")

LINKS_TERABYTE = [
    "https://www.terabyteshop.com.br/hardware/processadores",
    "https://www.terabyteshop.com.br/hardware/placas-de-video",
    "https://www.terabyteshop.com.br/monitores",
    "https://www.terabyteshop.com.br/cadeiras",
    "https://www.terabyteshop.com.br/perifericos",
    "https://www.terabyteshop.com.br/gabinetes",
    "https://www.terabyteshop.com.br/hardware/fontes",
    "https://www.terabyteshop.com.br/home-e-eletro",
    "https://www.terabyteshop.com.br/games"
]

def carregar_memoria():
    if not os.path.exists(ARQUIVO_MEMORIA): return []
    try:
        with open(ARQUIVO_MEMORIA, "r") as f: return f.read().splitlines()
    except: return []

def salvar_na_memoria(link):
    try:
        with open(ARQUIVO_MEMORIA, "a") as f: f.write(f"{link}\n")
    except: pass

ofertas_enviadas = carregar_memoria()

def iniciar_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    # PERFIL EXCLUSIVO PARA TERABYTE (Diferente do ML)
    caminho_perfil = os.path.join(os.getcwd(), "chrome_perfil_tb")
    options.add_argument(f"--user-data-dir={caminho_perfil}")
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver

def limpar_valor(texto):
    try:
        texto = texto.upper().replace('R$', '').strip()
        return float(texto.replace('.', '').replace(',', '.'))
    except: return 0.0

def limpar_link(link):
    return link.split('?')[0].split('#')[0]

def extrair_terabyte(driver):
    print(">>> Iniciando varredura Terabyte...")
    for url in LINKS_TERABYTE:
        try:
            driver.get(url)
            time.sleep(5) # Tempo pro Cloudflare
            produtos = driver.find_elements(By.CLASS_NAME, 'product-item')
            
            for prod in produtos[:6]:
                try:
                    if len(prod.find_elements(By.CLASS_NAME, 'tbt_esgotado')) > 0: continue

                    link_el = prod.find_element(By.CLASS_NAME, 'product-item__name')
                    raw_link = link_el.get_attribute('href')
                    link = limpar_link(raw_link)
                    
                    if link in ofertas_enviadas: continue
                    
                    nome = link_el.get_attribute('title')
                    
                    try:
                        div_novo = prod.find_element(By.CLASS_NAME, 'product-item__new-price')
                        preco_novo = limpar_valor(div_novo.find_element(By.TAG_NAME, 'span').text)

                        try:
                            div_antigo = prod.find_element(By.CLASS_NAME, 'product-item__old-price')
                            preco_antigo = limpar_valor(div_antigo.find_element(By.TAG_NAME, 'span').text)
                        except: preco_antigo = 0.0

                        if preco_antigo > 0 and preco_novo > 0:
                            pct = int(((preco_antigo - preco_novo) / preco_antigo) * 100)
                            topo = f"🔥 *TB • {pct}% OFF*"
                            linha_antigo = f"❌ De: R$ {preco_antigo:,.2f}"
                        else:
                            topo = "🔥 *OFERTA TERABYTE*"
                            linha_antigo = ""
                    except: continue

                    try:
                        img_url = prod.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    except: img_url = ""

                    msg = f"{topo}\n\n📦 {nome}\n{linha_antigo}\n✅ *Por: R$ {preco_novo:,.2f}*\n\n🔗 [GARANTIR AGORA]({link})"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Ir para Loja", url=link))
                    
                    bot.send_photo(CHAT_ID, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=markup)
                    print(f"✅ TB Enviado: {nome[:15]}")
                    ofertas_enviadas.append(link)
                    salvar_na_memoria(link)
                    time.sleep(2)
                except: continue
        except: pass

def job():
    global ofertas_enviadas
    ofertas_enviadas = carregar_memoria()
    driver = iniciar_driver()
    try:
        extrair_terabyte(driver)
    except: pass
    finally:
        try: driver.quit()
        except: pass
    print("--- Fim ciclo Terabyte (Pausa 2 min) ---")

if __name__ == "__main__":
    job()
    schedule.every(2).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)