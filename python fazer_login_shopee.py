import undetected_chromedriver as uc
import time
import os

# Define a mesma pasta de perfil que o bot usa
DIRETORIO_ATUAL = os.getcwd()
CAMINHO_PERFIL = os.path.join(DIRETORIO_ATUAL, "chrome_perfil_shopee")

print("--- MODO DE LOGIN MANUAL ---")
print(f"Salvando perfil em: {CAMINHO_PERFIL}")

options = uc.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-popup-blocking")
# O segredo: Usar o mesmo user-data-dir
options.add_argument(f"--user-data-dir={CAMINHO_PERFIL}")

driver = uc.Chrome(options=options, use_subprocess=True)

print(">>> Navegador aberto!")
print("1. Faça seu login na Shopee (Email/Senha ou QR Code).")
print("2. Se pedir SMS ou Captcha, resolva.")
print("3. Quando estiver logado na Home, pode fechar a janela.")

driver.get("https://shopee.com.br/buyer/login")

# Fica aberto por 10 minutos para dar tempo de você logar
time.sleep(600)