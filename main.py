#!/usr/bin/env python3
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kroot")

def main(args):
    with args.foodsfile as file:
        if query:=args.search:
            search_food_write_csv(query, file)
        if args.add:
            import csv
            rows = list(csv.DictReader(file))
            to_str = lambda i, item: f"{i}. {item['Name']} ({item['Portion']})\n"
            if indices:=iterator_fzf_select(rows, fzf_process(['--multi']), to_str=to_str):
                for i in indices:
                    item = rows[i]
                    print(f"How much of \"{item['Name']} ({item['Portion']})\" you consumed (float)?", end="\n> ")
                    while True:
                        try:
                            amount = float(input())
                            break
                        except ValueError:
                            print(end="> ")
                from datetime import datetime
                date = datetime.today()
                today_filename = date.strftime("%F.txt")
                print(args.atedir.joinpath(today_filename))

def search_food_write_csv(query, foodsfile):
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver import ChromeOptions, Chrome
    from more_itertools import take
    import csv
    global driver
    options = ChromeOptions()
    service = Service("/sbin/chromedriver")
    options.add_argument("--headless=new")
    driver = Chrome(options=options, service=service)
    keys = [ "Energy", "Protein", "Carbohydrate", "Sugar", "Cholesterol", "Fat", "Caffeine" ]
    units = {
            "Energy": "kcal"
            }
    if (name_url := prompt_url_fzf(query)):
        name, url = name_url
        writer = csv.writer(foodsfile)
        portions, select = get_portions_element(url)
        if len(portions) > 1:
            portion = select_portion_fzf(portions, select)
        else:
            portion = portions[0]
            logger.info(f"only one portion ({portion}) was present.")
        logger.info("reading keys from the selected food...")
        row = {key: value for key, value, _ in take(len(keys), get_keys(keys, units))}
        row["Name"] = name
        row["Portion"] = portion
        for key in keys:
            if not (item:=row.get(key,0)):
                row[key] = item
        writer = csv.DictWriter(foodsfile, ["Name", "Portion"]+keys, lineterminator="\n")
        reader = csv.reader(foodsfile)
        name_portions = [(name, portion) for name, portion, *_ in reader]
        if not any(name_portions):
            writer.writeheader()
        if (name, portion) not in name_portions:
            writer.writerow(row)
            logger.info(f"wrote \"{name}\" to csv file successfully.")
        else:
            logger.info("name and portion present. Didn't write the new one.")

def select_portion_fzf(portions, select):
    if indices:=iterator_fzf_select(portions, fzf_process()):
        i = indices[0]
        select.select_by_visible_text(portions[i])
        return portions[i]
    return portions[0]

def get_portions_element(url):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.select import Select
    from operator import attrgetter
    driver.get(url)
    selector = By.ID, "nutrient-per-selection-Survey-or-branded"
    element = WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    select = Select(element)
    return tuple(map(attrgetter("text"), select.options)), select

def get_keys(keys, units={}):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    WebDriverWait(driver, 5).until(EC.invisibility_of_element((By.ID, "floatingCirclesG")))
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
        if unit_ok and (key:=next((key for key in keys if key in name), None)) is not None:
            yield key, float(value), unit

def prompt_url_fzf(query):
    from selenium.common.exceptions import TimeoutException
    to_str = lambda i, name_url_cat: f"{i}. \"{name_url_cat[0]}\" in \"{name_url_cat[2]}\"\n"
    name_urls = []
    callback = lambda _, name_url: name_urls.append((name_url[0], name_url[1]))
    process = fzf_process()
    for type in ("Foundation","SR Legacy"):
        try:
            if indices:=iterator_fzf_select(search(query, type), process, callback, to_str):
                i = indices[0]
                return name_urls[i]
        except TimeoutException:
            pass
    process.terminate()
    process.wait()
    logger.error("No results.")
    exit(1)

def fzf_process(args=[]):
    import subprocess
    return subprocess.Popen(
            ["fzf"]+args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

def iterator_fzf_select(iterator,process, callback=None, to_str=lambda i, item: f"{i}. {item}\n"):
    if process.stdin is None or process.stdout is None:
        return
    try:
        for i, item in enumerate(iterator):
            if process.poll():
                break
            process.stdin.write(to_str(i, item))
            process.stdin.flush()
            if callback is not None:
                callback(i, item)
        process.stdin.close()
    except BrokenPipeError:
        pass
    if output:=process.stdout.readlines():
        return [int(line[:line.index(".")]) for line in output]


def search(query, type):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver import ActionChains
    from selenium.common.exceptions import StaleElementReferenceException
    driver.get(f"https://fdc.nal.usda.gov/food-search?type={type}&query={query}")
    selector = By.CSS_SELECTOR, "app-food-search>div>div>div>div>table>tbody>tr"
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    elements = driver.find_elements(*selector)
    i = 0
    while i < len(elements):
        element = elements[i]
        ActionChains(driver).scroll_to_element(element).perform()
        try:
            try:
                _, url_name, _, category, *_ = element.find_elements(By.XPATH,".//td")
                url = url_name.find_element(By.CSS_SELECTOR,"a").get_attribute("href")
                yield url_name.text, url, category.text
            except ValueError:
                _, url_name, category, *_ = element.find_elements(By.XPATH,".//td")
                url = url_name.find_element(By.CSS_SELECTOR,"a").get_attribute("href")
                yield url_name.text, url, category.text
            i+=1
        except StaleElementReferenceException:
            elements = driver.find_elements(*selector)

if __name__ == "__main__":
    from argparse import ArgumentParser, FileType
    from pathlib import Path
    parser = ArgumentParser(prog='kroot', description='(pronounced carrot) a script for you to gather data about food you eat')
    parser.add_argument('--search', type=str, help="search food in the USDA's database")
    parser.add_argument('--add', help="interactively add nom nom-ed food", action="store_true")
    parser.add_argument('--foodsfile', type=FileType("r+"), default="/home/nima/.config/havij/foods.csv")
    parser.add_argument('--atedir', type=Path, default="/home/nima/.config/havij/ate/")
    args = parser.parse_args()
    main(args)
