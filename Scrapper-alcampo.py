import time
import re
import os
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from bs4 import BeautifulSoup

# Variable global para controlar el primer llamado
primer_llamado = True

# Función para abrir el navegador
def abrir_navegador():
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        return webdriver.Chrome(options=options)  # Asegúrate de tener chromedriver en tu PATH
    except Exception as e:
        print("Error al abrir el navegador:", e)
        return None

# Función para cerrar el banner de cookies
def cerrar_banner_cookies(driver):
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "onetrust-banner-sdk")))
        accept_cookies_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        accept_cookies_button.click()
        print("Banner de cookies cerrado exitosamente.")
    except Exception as e:
        print("Banner de cookies no encontrado o no se pudo cerrar:", e)

# Función para cerrar el modal
def cerrar_modal(driver):
    try:
        modal_close_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "box-close"))
        )
        modal_close_button.click()
        print("Modal cerrado exitosamente.")
    except Exception as e:
        print("Modal no encontrado o no se pudo cerrar:", e)

# Función para cargar todos los elementos de la página
def esperar_carga_imagenes(driver):
    try:
        images = driver.find_elements(By.TAG_NAME, 'img')
        for image in images:
            WebDriverWait(driver, 10).until(
                EC.visibility_of(image)
            )
        print("Todas las imágenes se han cargado.")
    except Exception as e:
        print("Error al esperar la carga de las imágenes:", e)

# Función para hacer clic en una categoría
def hacer_clic_en_categoria(driver, categoria):
    try:
        enlace_categoria = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, f"//a[@data-test='root-category-link' and text()='{categoria}']"))
        )
        enlace_categoria.click()
        time.sleep(2)  # Espera 2 segundos después de hacer clic en la categoría
        return True
    except Exception as e:
        print(f"No se pudo hacer clic en la categoría '{categoria}':", e)
        return False

# Función para extraer las categorías
def obtener_categorias(driver, excluir_primera=True):
    global primer_llamado
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "list__StyledList-sc-bv01u5-1")))
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        categorias = soup.find_all("a", attrs={"data-test": "root-category-link"})
        
        # Excluir la primera categoría solo en el primer llamado si se indica
        if excluir_primera and primer_llamado:
            categorias_texto = [categoria.text.strip() for categoria in categorias[1:]]
            primer_llamado = False
        else:
            categorias_texto = [categoria.text.strip() for categoria in categorias]

        return categorias_texto
    except Exception as e:
        print("Error al obtener las categorías:", e)
        return []
    
def scrape_productos(driver, categoria_padre, subcategoria, categoria_padre_anterior=None, categoria_anterior=None, productos_procesados=set()):
    start_time = time.time()  # Guardamos el tiempo de inicio
    try:
        productos = []
        total_elementos = 0

        # Hacer scroll hasta la mitad de la página para cargar más elementos
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)  # Esperar un momento para que se complete el desplazamiento

        while time.time() - start_time < 60:
            try:
                nuevos_elementos = driver.find_elements(By.XPATH, "//a[@data-test='fop-product-link']")
                driver.execute_script("window.scrollTo(0, 0);")

                if len(nuevos_elementos) > total_elementos:
                    elementos_productos = nuevos_elementos
                    total_elementos = len(elementos_productos)

                    # Hacer scroll hasta el último elemento de cada grupo de 8 elementos
                    for i in range(total_elementos // 8 + 1):
                        start_index = i * 8
                        end_index = min((i + 1) * 8, total_elementos)

                        elemento = elementos_productos[end_index - 1]
                        driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                        time.sleep(0.5)  # Esperar un momento para que se complete el desplazamiento

                else:
                    print("La cantidad de elementos cargados es menor o igual a la anterior")
                    break  # Salir del bucle while si no hay nuevos elementos
            except StaleElementReferenceException:
                print("Elemento de referencia caduco. Reintentando...")
                continue
       
        # Una vez que se hayan cargado todos los elementos, extraer los detalles de los productos
        html_content = driver.page_source
        productos += parse_productos(html_content, categoria_padre, subcategoria, categoria_padre_anterior, categoria_anterior, productos_procesados)

        return productos

    except Exception as e:
        print("Error al obtener detalles de los productos:", e)
        return []

def parse_productos(html_content, categoria_padre, subcategoria, categoria_padre_anterior, categoria_anterior, productos_procesados):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        productos_containers = soup.find_all('div', class_='product-card-container')
        
        productos = []
        for producto in productos_containers:
            nombre_element = producto.find('h3', class_='_text_f6lbl_1')
            nombre = nombre_element.text.strip() if nombre_element else "Nombre no disponible"

            if nombre in productos_procesados:
                continue

            imagen_element = producto.find('img', class_='image__StyledLazyLoadImage-sc-wislgi-0')
            imagen_url = imagen_element.get('src').strip() if imagen_element else "URL de imagen no disponible"

            # Limpiar el precio para eliminar caracteres no deseados
            precio_element = producto.find('span', class_='price__PriceText-sc-1nlvmq9-0')
            precio = precio_element.text.strip() if precio_element else "Precio no disponible"
            precio = re.sub(r'[^\d.,]', '', precio)  # Eliminar todo excepto números, punto decimal y coma

            # Verificar si el producto está agotado
            agotado = producto.find('span', class_='_badge__text_tex7q_63')
            if agotado and agotado.text.strip() == 'Agotado':
                print(f"El producto '{nombre}' está agotado. No será incluido en los resultados.")
                continue  # Continuar al siguiente producto, no procesar este

            if nombre == "Nombre no disponible" or imagen_url == "URL de imagen no disponible" or precio == "Precio no disponible":
                print(f"El producto '{nombre}' no tiene todos los datos completos. No será incluido en los resultados.")
                continue  # Saltar productos incompletos

            productos_procesados.add(nombre)

            productos.append({
                "supermercado": "alcampo",
                "categoria_padre": categoria_padre,
                "subcategoria": subcategoria,
                "categoria_padre_anterior": categoria_padre_anterior,
                "categoria_anterior": categoria_anterior,
                "nombre": nombre,
                "imagen_url": imagen_url,
                "precio": precio
            })
        
        return productos

    except Exception as e:
        print("Error al analizar los detalles de los productos:", e)
        return []

# Función para guardar los datos en un archivo CSV
def guardar_en_csv(producto):
    file_exists = os.path.isfile('productos.csv')
    with open('productos.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            # Escribir la cabecera solo si el archivo no existe
            writer.writerow(["supermercado", "categoria_padre", "subcategoria", "categoria_padre_anterior", "categoria_anterior", "nombre", "imagen_url", "precio"])
        writer.writerow([
            producto["supermercado"],
            producto["categoria_padre"],
            producto["subcategoria"],
            producto["categoria_padre_anterior"],
            producto["categoria_anterior"],
            producto["nombre"],
            producto["imagen_url"],
            producto["precio"]
        ])

# Función para iterar sobre las categorías y subcategorías
def iterar_categorias(driver, categorias, productos_procesados, categoria_padre=None, categoria_padre_anterior=None):
    for categoria in categorias:
        if hacer_clic_en_categoria(driver, categoria):
            subcategorias = obtener_categorias(driver, excluir_primera=False)
            time.sleep(1)  # Espera 1 segundo después de obtener las subcategorías
            
            if subcategorias:
                for subcategoria in subcategorias:
                    if hacer_clic_en_categoria(driver, subcategoria):
                        time.sleep(2)  # Espera 2 segundos después de hacer clic en la subcategoría
                        datos_productos = scrape_productos(driver, categoria, subcategoria, categoria_padre, productos_procesados=productos_procesados)
                        for producto in datos_productos:
                            print(f"Datos de productos en la subcategoría '{subcategoria}' de la categoría '{categoria}':")
                            guardar_en_csv(producto)

                        # Volver atrás a la categoría padre
                        driver.back()
                        time.sleep(2)  # Espera 2 segundos después de volver atrás
                    else:
                        print(f"No se pudieron obtener los datos de la subcategoría '{subcategoria}'")

            # Volver atrás a la categoría principal
            driver.back()
            time.sleep(2)  # Espera 2 segundos después de volver atrás
        else:
            print(f"No se pudieron obtener los datos de la categoría '{categoria}'")

# Inicializar el navegador y abrir la página web
driver = abrir_navegador()
if driver:
    try:
        url_inicial = "https://www.compraonline.alcampo.es/categories"
        driver.get(url_inicial)

        cerrar_banner_cookies(driver)
        cerrar_modal(driver)

        categorias_iniciales = obtener_categorias(driver)
        time.sleep(4)
        productos_procesados = set()  # Conjunto para almacenar productos ya procesados
        iterar_categorias(driver, categorias_iniciales, productos_procesados)

    finally:
        driver.quit()
