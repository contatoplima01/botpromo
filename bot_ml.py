import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import schedule
import time
import os
import re
import random

# --- CONFIGURAÇÕES ---
TOKEN = ''
CHAT_ID = ''
bot = telebot.TeleBot(TOKEN)

# Links do Mercado Livre
LINKS_ML = [
    "https://lista.mercadolivre.com.br/informatica/placa-video",
    "https://lista.mercadolivre.com.br/celulares-telefones/celulares-smartphones/iphone",
    "https://lista.mercadolivre.com.br/informatica/monitores",
    "https://lista.mercadolivre.com.br/cadeira-gamer"
]

ARQUIVO_MEMORIA = "historico_ids_ml.txt"
if not os.path.exists(ARQUIVO_MEMORIA): 
    with open(ARQUIVO_MEMORIA, 'w') as f: pass

def carregar_memoria():
    with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def salvar_id(id_produto):
    with open(ARQUIVO_MEMORIA, "a", encoding="utf-8") as f:
        f.write(f"{id_produto}\n")

ids_enviados = carregar_memoria()

def iniciar_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    # Pasta de perfil exclusiva para o ML
    caminho_perfil = os.path.join(os.getcwd(), "chrome_perfil_ml")
    options.add_argument(f"--user-data-dir={caminho_perfil}")
    
    # --- CORREÇÃO DO ERRO DE VERSÃO ---
    # Forçamos o uso da versão 144 para bater com o seu Chrome instalado
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=144)
    return driver

def extrair_id_ml(link):
    # O ID no ML geralmente fica após /MLB-
    match = re.search(r'MLB-?(\d+)', link)
    if match: return "MLB-" + match.group(1)
    return None

def extrair_ml(driver):
    global ids_enviados
    print(">>> Iniciando varredura Mercado Livre...")
    
    for url in LINKS_ML:
        try:
            print(f"   -> Navegando: {url}...")
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            # Cards do ML (Pode variar, tenta os dois padrões comuns)
            items = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "div.ui-search-result__wrapper")
            
            print(f"      Itens encontrados: {len(items)}")

            count = 0
            for item in items:
                if count >= 5: break
                try:
                    # Link
                    try:
                        link_el = item.find_element(By.TAG_NAME, "a")
                        href = link_el.get_attribute("href")
                    except: continue

                    uid = extrair_id_ml(href)
                    if not uid or uid in ids_enviados: continue

                    # Texto
                    texto_completo = item.text
                    linhas = texto_completo.split('\n')
                    
                    # Tenta achar preço
                    precos = re.findall(r'R\$\s?([\d\.,]+)', texto_completo)
                    if not precos: continue
                    
                    # Limpeza de valor
                    valor_atual = float(precos[0].replace('.', '').replace(',', '.'))
                    
                    # Nome (Geralmente a primeira linha que não seja 'Patrocinado')
                    nome = linhas[0]
                    if len(nome) < 10 and len(linhas) > 1: nome = linhas[1]

                    # Filtros básicos
                    if "usado" in texto_completo.lower(): continue

                    # Imagem
                    try:
                        img_el = item.find_element(By.TAG_NAME, "img")
                        img_url = img_el.get_attribute("src")
                    except: img_url = "https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png"

                    # Envio
                    msg = f"💛 *MERCADO LIVRE*\n\n📦 {nome}\n✅ *R$ {valor_atual:,.2f}*\n\n🔗 [Ver no ML]({href})"
                    
                    kb = InlineKeyboardMarkup()
                    kb.add(InlineKeyboardButton("Ver Oferta", url=href))

                    try:
                        bot.send_photo(CHAT_ID, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=kb)
                    except:
                        bot.send_message(CHAT_ID, msg, parse_mode='Markdown', reply_markup=kb)

                    print(f"✅ Enviado ML: {uid}")
                    ids_enviados.add(uid)
                    salvar_id(uid)
                    count += 1
                    time.sleep(2)

                except: continue
        except Exception as e:
            print(f"Erro URL ML: {e}")

def job():
    driver = iniciar_driver()
    try: extrair_ml(driver)
    except: pass
    finally:
        try: driver.quit()
        except: pass
    print("--- Fim ciclo ML ---")

if __name__ == "__main__":
    print("Bot ML Iniciado (Versão 144 Fix)...")
    job()
    schedule.every(10).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)