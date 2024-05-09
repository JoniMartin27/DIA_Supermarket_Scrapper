import csv
import os
import time
import threading
import random  # Importa el módulo random

import requests
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unidecode import unidecode


class DIAScrapper(object):
    search_url = 'https://www.compraonline.alcampo.es/categories/frescos'

    def __init__(self):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36")

        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.driver.implicitly_wait(5)
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
                # Wait for the cookie banner to appear
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "onetrust-banner-sdk")))
                # Close the cookie banner
                accept_cookies_button = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                accept_cookies_button.click()
                print("Cookie banner closed successfully.")
            except TimeoutException:
                print("Cookie banner not found or unable to close.")

            self.cerrar_cookies = 1
            try:
                # Espera hasta que aparezca el modal
                modal = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "div.delivery-book-modal-content")))

                # Encuentra el botón o enlace para cerrar el modal
                close_button = WebDriverWait(modal, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.box-close"]')))

                # Haz clic en el botón para cerrar el modal
                close_button.click()

                print("Modal cerrado exitosamente.")

            except Exception as e:
                print("Error al cerrar el modal:", e)


        while True:
            categories = self.driver.find_elements(By.CSS_SELECTOR, 'a.link__Link-sc-14ymsi2-0 bgwHFk link__Link-sc-14ymsi2-0 nav-list-item__StyledNavListItemLink-sc-avd605-1 bgwHFk hBPgqm')
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
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span._text_f6lbl_1 _text--m_f6lbl_23')))
            self.recursive_scrape_subcategories()

    def recursive_scrape_subcategories(self):
        while True:
            time.sleep(2)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span._text_f6lbl_1 _text--m_f6lbl_23')))
            except TimeoutException:
                print("Timeout occurred while waiting for subcategory element.")
                continue  # Skip to the next iteration of the loop

            visited_subcategories_in_category = set()
            subcategories = self.driver.find_elements(By.CSS_SELECTOR, 'span._text_f6lbl_1 _text--m_f6lbl_23')
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
            productos = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-test-id="fop-wrapper:65731ee6-48c6-44f3-a504-698fb6c62f25]')

            current_product_count = len(productos)

            if current_product_count == previous_product_count:
                break

            for producto in productos:
                try:
                    nombre = producto.find_element(By.CSS_SELECTOR, 'h3._text_f6lbl_1 _text--m_f6lbl_23').text
                    precio = producto.find_element(By.CSS_SELECTOR, 'span._text_f6lbl_1 _text--m_f6lbl_23 price__PriceText-sc-1nlvmq9-0 BCfDm').text
                    image_url = producto.find_element(By.CSS_SELECTOR,
                                                      'img.image_StyledLazyLoadImage-sc-wilgi-0.foQxui').get_attribute('src')
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
