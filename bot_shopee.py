from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import os
import re
import random

# --- CONFIGURAÇÕES ---
TOKEN = ''
CHAT_ID = ''
bot = telebot.TeleBot(TOKEN)

INTERVALO_TIMER = 600  # 10 minutos

LINKS_SHOPEE = [
    "https://shopee.com.br/flash_deals", 
    "https://shopee.com.br/search?keyword=placa%20de%20video",
    "https://shopee.com.br/search?keyword=iphone",
    "https://shopee.com.br/search?keyword=monitor",
    "https://shopee.com.br/search?keyword=cadeira%20gamer"
]

PALAVRAS_BLOQUEADAS = [
    "usado", "usada", "seminovo", "semi-novo", "recondicionado", "vitrine", 
    "defeito", "risco", "riscos", "avaria", "quebrado", "peças", "sucata", 
    "no estado", "outlet", "grade a", "grade b", "mostruário", "detalhe"
]

ARQUIVO_MEMORIA = "historico_ids_shopee.txt"
if not os.path.exists(ARQUIVO_MEMORIA): 
    with open(ARQUIVO_MEMORIA, 'w') as f: pass

def carregar_memoria():
    with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def salvar_id(id_produto):
    with open(ARQUIVO_MEMORIA, "a", encoding="utf-8") as f:
        f.write(f"{id_produto}\n")

ids_enviados = carregar_memoria()

def conectar_chrome_existente():
    print("🔌 Conectando ao seu Chrome (Porta 9222)...")
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def verificar_bloqueio_manual(driver):
    frases_erro = ["verify/captcha", "erro de carregamento", "traffic control", "estamos enfrentando alguns problemas"]
    bloqueado = False
    try:
        url_atual = driver.current_url.lower()
        src_atual = driver.page_source.lower()
        if any(f in url_atual for f in frases_erro) or any(f in src_atual for f in frases_erro):
            bloqueado = True

        if bloqueado:
            print("\n" + "="*50)
            print("🚨🚨 BLOQUEIO SHOPEE DETECTADO! 🚨🚨")
            print(">>> Resolva manualmente no navegador. <<<")
            print("="*50 + "\n")
            while bloqueado:
                time.sleep(5)
                try:
                    url_nova = driver.current_url.lower()
                    src_novo = driver.page_source.lower()
                    if not any(f in url_nova for f in frases_erro) and not any(f in src_novo for f in frases_erro):
                        print("✅ Resolvido! Retomando...")
                        time.sleep(5)
                        return True
                except: pass
            return True
    except: pass
    return False

def limpar_valor(texto):
    try:
        if "-" in texto: texto = texto.split("-")[0]
        texto = texto.upper().replace('R$', '').replace('PIX', '').strip()
        return float(texto.replace('.', '').replace(',', '.'))
    except: return 0.0

def analisar_extras(texto_card, preco_novo):
    extras = []
    text = texto_card.lower()
    if "frete grátis" in text: extras.append("🚚 Frete Grátis")
    if "cupom" in text: extras.append("🎟️ Cupom de Loja")
    if "cashback" in text: extras.append("💰 Ganhe Cashback")
    
    # Procura selo de OFF para adicionar aos extras e ajudar no cálculo reverso
    pct_off = 0
    match = re.search(r'-?(\d+)%\s?(?:off)?', text)
    if match: 
        pct_off = int(match.group(1))
        extras.append(f"📉 Selo {pct_off}% OFF")

    desc = preco_novo * 0.25
    qtd = int(desc * 100)
    final = preco_novo - desc
    return extras, qtd, final, pct_off

def extrair_parcelamento(texto_card):
    match = re.search(r'(\d{1,2})\s?[xX].{0,10}R\$\s?([\d\.,]+)', texto_card)
    if match:
        return f"💳 {match.group(1)}x de R$ {match.group(2)}" + (" (sem juros)" if "sem juros" in texto_card.lower() else "")
    return ""

def extrair_imagem_forcada(driver, item_link):
    url_img = ""
    try:
        imgs = item_link.find_elements(By.CSS_SELECTOR, "img.w-full")
        for i in imgs:
            src = i.get_attribute("src")
            if src and "http" in src and "data:image" not in src:
                url_img = src; break
        
        if not url_img:
            divs = item_link.find_elements(By.TAG_NAME, "div")
            for d in divs:
                bg = d.value_of_css_property("background-image")
                if bg and "url" in bg and "http" in bg:
                    url_img = bg.replace('url("', '').replace('")', '').replace('"', '')
                    break
        
        if not url_img:
             imgs = item_link.find_elements(By.TAG_NAME, "img")
             for i in imgs:
                 src = i.get_attribute("src")
                 if src and "http" in src:
                     alt = str(i.get_attribute("alt")).lower()
                     if "icon" in src or "badge" in src or "overlay" in alt: continue
                     url_img = src; break
    except: pass
    if not url_img: url_img = "https://cf.shopee.com.br/file/br-50009109-c12e20b335342371900d720b0858102d"
    return url_img

def ciclo_shopee(driver):
    global ids_enviados
    print(f"\n--- Varrendo Shopee (Modo Espelho - Timer {INTERVALO_TIMER/60:.0f} min) ---")
    
    for url in LINKS_SHOPEE:
        try:
            print(f"-> Indo para: {url}...")
            driver.get(url)
            time.sleep(5)
            
            if verificar_bloqueio_manual(driver):
                driver.get(url)
                time.sleep(5)

            driver.execute_script("window.scrollBy(0, 700);")
            time.sleep(2)
            
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='-i.']")
            items_unicos = []
            seen = set()
            for l in links:
                h = l.get_attribute('href')
                if h and h not in seen:
                    items_unicos.append(l)
                    seen.add(h)
            
            print(f"   Itens encontrados: {len(items_unicos)}")

            count = 0
            for item in items_unicos:
                if count >= 5: break

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                    time.sleep(0.5)

                    href = item.get_attribute('href')
                    match_id = re.search(r'i\.(\d+\.\d+)', href)
                    uid = match_id.group(1) if match_id else None
                    if not uid or uid in ids_enviados: continue

                    try:
                        full_text = item.text
                        if len(full_text) < 10: full_text = item.find_element(By.XPATH, "./..").text
                    except: full_text = ""

                    # --- CORREÇÃO DE NOME ---
                    # Pega a primeira linha que NÃO seja curta e NÃO tenha %
                    linhas = full_text.split('\n')
                    nome = "Oferta Shopee"
                    for l in linhas:
                        l_limpa = l.strip()
                        if len(l_limpa) > 4 and "%" not in l_limpa and "R$" not in l_limpa:
                            nome = l_limpa
                            break
                    
                    # Filtro Usados
                    if any(bad in (nome + full_text).lower() for bad in PALAVRAS_BLOQUEADAS): continue

                    # Preços
                    precos = re.findall(r'R\$\s?[\d\.,]+', full_text)
                    if not precos: continue
                    vals = sorted([limpar_valor(p) for p in precos])
                    novo = vals[0]
                    antigo = vals[-1] if len(vals) > 1 else 0
                    if novo == 0: continue

                    # Extras e Porcentagem
                    img = extrair_imagem_forcada(driver, item)
                    lista_ext, moedas, final_moedas, pct_encontrada = analisar_extras(full_text, novo)
                    parcela_txt = extrair_parcelamento(full_text)

                    # --- CÁLCULO REVERSO DE PREÇO ANTIGO ---
                    # Se não achou preço antigo explícito, mas achou a porcentagem (ex: -14%)
                    if antigo == 0 and pct_encontrada > 0:
                        try:
                            antigo = novo / (1 - (pct_encontrada / 100))
                        except: pass

                    str_extras = "\n🎁 *EXTRAS:*\n" + "\n".join([f"• {e}" for e in lista_ext]) if lista_ext else ""
                    str_moedas = f"\n\n🪙 *COM MOEDAS (25% OFF):*\n• Use: {moedas} moedas\n• *Valor Final:* R$ {final_moedas:,.2f}"
                    linha_parcela = f"\n{parcela_txt}" if parcela_txt else ""
                    
                    if antigo > novo:
                        # Recalcula porcentagem real para garantir precisão
                        pct_real = int(((antigo - novo) / antigo) * 100)
                        topo = f"🧡 *SHOPEE • {pct_real}% OFF*"
                        linha_ant = f"❌ De: R$ {antigo:,.2f}"
                    else:
                        topo = "🧡 *OFERTA SHOPEE*"
                        linha_ant = ""

                    msg = f"{topo}\n\n📦 {nome}\n{linha_ant}\n✅ *Por: R$ {novo:,.2f}*{linha_parcela}\n{str_extras}{str_moedas}\n\n⚠️ _Cupons funcionam melhor no App_"

                    kb = InlineKeyboardMarkup()
                    kb.add(InlineKeyboardButton("📲 Abrir no App", url=href))
                    kb.add(InlineKeyboardButton("💻 Ver no Site", url=href))

                    try:
                        bot.send_photo(CHAT_ID, photo=img, caption=msg, parse_mode='Markdown', reply_markup=kb)
                    except:
                        bot.send_message(CHAT_ID, msg, parse_mode='Markdown', reply_markup=kb)

                    print(f"   ✅ Enviado: {uid}")
                    ids_enviados.add(uid)
                    salvar_id(uid)
                    count += 1
                    time.sleep(random.uniform(2, 4))

                except: continue
            verificar_bloqueio_manual(driver)
                    
        except Exception as e:
            print(f"Erro geral na URL: {e}")

if __name__ == "__main__":
    try:
        driver = conectar_chrome_existente()
        print(f">>> Bot Conectado! Timer: {INTERVALO_TIMER/60:.0f} min.")
        while True:
            ciclo_shopee(driver)
            print(f"--- Aguardando {INTERVALO_TIMER/60:.0f} minutos ---")
            time.sleep(INTERVALO_TIMER)
    except Exception as e:
        print("\n❌ ERRO: Não achei o Chrome.")
        print("Rode este comando no terminal ANTES de iniciar o bot:")
        print(r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromePerfilBot"')