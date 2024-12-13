import more_itertools
import string, time
import subprocess
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException, StaleElementReferenceException
from urllib3.connectionpool import sys

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
# driver = webdriver.Firefox()

def get_keys(keys, url, units={}):
    driver.get(url)
    selector = By.CSS_SELECTOR, "app-food-nutrients>div>div>table>tbody>tr"
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))

    for item in driver.find_elements(*selector):
        try:
            name, value, unit, *_ = map(lambda x: x.text.strip(), item.find_elements(By.XPATH,".//td"))
        except ValueError:
            continue
        try:
            unit_ok = units[name] == unit
        except KeyError:
            unit_ok = True
        # for key in 

        if unit_ok and any(key in name for key in keys):
            yield name, value, unit


def search(query):
    driver.get(f"https://fdc.nal.usda.gov/food-search?type=Foundation&query={query}")
    selector = By.CSS_SELECTOR, "app-food-search>div>div>div>div>table>tbody>tr"
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    elements = driver.find_elements(*selector)
    i = 0
    while i < len(elements):
        element = elements[i]
        webdriver.ActionChains(driver).scroll_to_element(element).perform()
        try:
            try:
                _, url_name, _, category, *_ = element.find_elements(By.XPATH,".//td")
            except ValueError:
                continue
            url = url_name.find_element(By.CSS_SELECTOR,"a").get_attribute("href")
            yield url_name.text, url, category.text
            i+=1
        except StaleElementReferenceException:
            elements = driver.find_elements(*selector)


# url = "https://fdc.nal.usda.gov/food-details/747997/nutrients"
# print(list(more_itertools.take(len(keys), get_keys(keys, url, units))))
# print(list(search("milk")))

# keys = [ "Energy", "Protein", "Carbohydrate", "Sugar" ]
# units = {
#         "Energy": "kcal"
#         }

process = subprocess.Popen(
        "fzf",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True 
    )

urls = []
for i, (name, url, category) in enumerate(search(sys.argv[1])):
    if process.poll():
        break
    process.stdin.write(f"{i}. \"{name}\" in \"{category}\"\n")
    process.stdin.flush()
    urls.append(url)
process.stdin.close()
if output:=process.stdout.read():
    index = int(output[:output.index(".")])
    print(urls[index])
else:
    print("nothing selected")
