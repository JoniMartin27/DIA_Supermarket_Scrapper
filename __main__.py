import csv
import os
import time
import threading
import random  # Importa el módulo random

import requests
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unidecode import unidecode


class DIAScrapper(object):
    search_url = 'https://www.dia.es/charcuteria-y-quesos/jamon-cocido-lacon-fiambres-y-mortadela/c/L2001'

    def __init__(self):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36")

        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.driver.implicitly_wait(2)
        self.visited_categories = set()
        self.visited_subcategories = set()
        self.products = []
        self.cerrar_cookies = 0
        self.csv_file = open('products.csv', 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(
            ['Producto', 'Precio', 'URL Imagen', 'Nutriscore'])  # Añadir 'Nutriscore'

    def __del__(self):
        try:
            self.csv_file.close()
        except AttributeError:
            pass

    def scrape_categories(self, url):
        time.sleep(2)
        self.driver.get(url)
        if self.cerrar_cookies == 0:
            time.sleep(5)
            try:
                # Espera hasta que la página esté completamente cargada
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "onetrust-banner-sdk")))
                # Cierra el aviso de cookies
                accept_cookies_button = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                accept_cookies_button.click()
                print("Aviso de cookies cerrado exitosamente.")
            except Exception as e:
                print("Error al cerrar el aviso de cookies:", e)
            self.cerrar_cookies = 1

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
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sub-category-item__text')))
            self.recursive_scrape_subcategories()

    def recursive_scrape_subcategories(self):
        while True:
            time.sleep(2)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.sub-category-item__text')))

            visited_subcategories_in_category = set()
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
            time.sleep(2)
            self.scrape_productos()

    def scrape_productos(self):
        scroll_thread = threading.Thread(target=self.scroll_down_slowly)
        scroll_thread.start()

        previous_product_count = 0

        while True:
            productos = self.driver.find_elements(By.CSS_SELECTOR, 'li[data-test-id="product-card-list-item"]')

            current_product_count = len(productos)

            if current_product_count == previous_product_count:
                break

            for producto in productos:
                try:
                    nombre = producto.find_element(By.CSS_SELECTOR, 'p.search-product-card__product-name').text
                    precio = producto.find_element(By.CSS_SELECTOR, 'p.search-product-card__active-price').text
                    image_url = producto.find_element(By.CSS_SELECTOR,
                                                      'img.search-product-card__product-image').get_attribute('src')
                    nombre = unidecode(nombre)
                    if nombre not in self.products:
                        self.products.append(nombre)
                        print("Producto:", nombre)
                        print("Precio:", precio)
                        print("Imagen URL:", image_url)
                        nutriscore = self.generate_nutriscore()  # Genera un Nutriscore aleatorio
                        print("Nutriscore:", nutriscore)
                        print("----------------------------------")
                        self.csv_writer.writerow(
                            ['', '', nombre, precio, image_url, nutriscore])  # Escribe el Nutriscore en el archivo CSV
                except NoSuchElementException:
                    pass
                except Exception as e:
                    print("Error:", e)
                    continue

            previous_product_count = current_product_count

    def generate_nutriscore(self):
        nutriscores = ['A', 'B', 'C', 'D', 'E']  # Lista de posibles Nutriscores
        return random.choice(nutriscores)  # Devuelve un Nutriscore aleatorio

    def scroll_down_slowly(self):
        while True:
            self.driver.execute_script("window.scrollBy(0, 5);")


if __name__ == "__main__":
    scrapper = DIAScrapper()
    scrapper.scrape_categories(DIAScrapper.search_url)
