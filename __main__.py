import time
import threading
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DIAScrapper(object):
    search_url = 'https://www.dia.es/charcuteria-y-quesos/jamon-cocido-lacon-fiambres-y-mortadela/c/L2001'

    def __init__(self):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36")

        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(2)
        self.visited_categories = set()  # Conjunto para almacenar los enlaces de categorías visitadas
        self.visited_subcategories = set()  # Conjunto para almacenar los enlaces de subcategorías visitadas
        self.products = []  # Lista para almacenar los productos

    def scrape_categories(self, url):
        self.driver.get(url)
        while True:
            categories = self.driver.find_elements(By.CSS_SELECTOR, 'a.category-item-link')
            next_category_link = None
            for category in categories:
                category_href = category.get_attribute('href')
                if category_href not in self.visited_categories:
                    next_category_link = category
                    self.visited_categories.add(category_href)
                    break

            if next_category_link is None:
                break

            print("Categoria:", next_category_link.text)
            next_category_link.click()
            # Esperar a que las subcategorías se carguen
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sub-category-item__text')))
            self.recursive_scrape_subcategories()

    def recursive_scrape_subcategories(self):
        while True:
            # Volver a cargar las subcategorías en cada iteración
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sub-category-item__text')))

            visited_subcategories_in_category = set()  # Conjunto para almacenar los enlaces de subcategorías visitadas en la categoría actual
            subcategories = self.driver.find_elements(By.CSS_SELECTOR, 'span.sub-category-item__text')
            next_subcategory_link = None
            for subcategory in subcategories:
                try:
                    if subcategory.is_displayed():
                        subcategory_href = subcategory.find_element(By.XPATH, './ancestor::a').get_attribute('href')
                        if subcategory_href not in self.visited_subcategories and subcategory_href not in visited_subcategories_in_category:
                            print("Subcategoria:", subcategory.text)
                            next_subcategory_link = subcategory
                            self.visited_subcategories.add(subcategory_href)
                            visited_subcategories_in_category.add(subcategory_href)
                            break
                except StaleElementReferenceException:
                    continue

            if next_subcategory_link is None:
                break

            next_subcategory_link.click()
            # Esperar a que las subcategorías se carguen
            time.sleep(1)  # Esperar 1 segundo después de entrar en cada subcategoría
            self.scrape_productos()

    def scrape_productos(self):
        # Iniciar un hilo para hacer scroll hacia abajo gradualmente
        scroll_thread = threading.Thread(target=self.scroll_down_slowly)
        scroll_thread.start()

        previous_product_count = 0  # Contador para el número de productos en la iteración anterior

        while True:
            # Obtener los productos después de cada desplazamiento
            productos = self.driver.find_elements(By.CSS_SELECTOR, 'li[data-test-id="product-card-list-item"]')

            current_product_count = len(productos)  # Contar el número actual de productos

            if current_product_count == previous_product_count:
                break  # Si el número de productos no ha cambiado, salir del bucle

            for producto in productos:
                try:
                    nombre = producto.find_element(By.CSS_SELECTOR, 'p.search-product-card__product-name').text
                    precio = producto.find_element(By.CSS_SELECTOR, 'p.search-product-card__active-price').text
                    if nombre not in self.products:  # Verificar si el producto ya ha sido guardado
                        self.products.append(nombre)
                        print("Producto:", nombre)
                        print("Precio:", precio)
                        print("----------------------------------")
                except NoSuchElementException:
                    pass  # No es necesario romper el bucle interno aquí

            previous_product_count = current_product_count

    def scroll_down_slowly(self):

        while True:
            # Incrementar el desplazamiento de manera más gradual
            self.driver.execute_script("window.scrollBy(0, 10);")  # Cambia el valor de 10 según la velocidad deseada


if __name__ == "__main__":
    scrapper = DIAScrapper()
    scrapper.scrape_categories(DIAScrapper.search_url)