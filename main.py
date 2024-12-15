#!/usr/bin/env python3


def main(args):
    with args.foodsfile as file:
        if query:=args.search:
            search_food_write_csv(query, file)
        if args.add:
            import csv
            rows = list(csv.DictReader(file))
            to_str = lambda i, item: f"{i}. {item['Name']} ({item['Portion']})\n"
            if indices:=iterator_fzf_select(rows, fzf_process(['--multi']), to_str=to_str):
                time = datetime.today()
                path = args.atedir.joinpath(time.strftime("%F.csv"))
                with open(path, "r+") as atefile:
                    writer = csv.DictWriter(atefile, list(rows[0].keys())+["Time", "Amount"])
                    if not atefile.read():
                        writer.writeheader()
                    for i in indices:
                        item = rows[i]
                        item["Time"] = time.strftime("%T")
                        print(f"How much of \"{item['Name']} ({item['Portion']})\" you consumed (float)?", end="\n> ")
                        while True:
                            try:
                                amount = float(input())
                                break
                            except ValueError:
                                print(end="> ")
                        item["Amount"] = amount
                        writer.writerow(item)
                        logger.info(f"wrote to file {path}")

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
    reader = csv.reader(foodsfile)
    name_portions = [(name, portion) for name, portion, *_ in reader]
    writer = csv.DictWriter(foodsfile, ["Name", "Portion"]+keys, lineterminator="\n")
    if not any(name_portions):
        writer.writeheader()
    for name, url in prompt_url_fzf(query):
        portions, select = get_portions_element(url)
        for portion in select_portions_fzf(portions, select, prompt=f"{name}> "):
            logger.info(f"reading keys for \"{name}\" ({portion}) ...")
            row = {key: value for key, value, _ in take(len(keys), get_keys(keys, units))}
            row["Name"] = name
            row["Portion"] = portion
            for key in keys:
                if not (item:=row.get(key,0)):
                    row[key] = item
            if (name, portion) not in name_portions:
                writer.writerow(row)
                logger.info(f"wrote \"{name}\" to csv file successfully.")
            else:
                logger.info("name and portion present. didn't write the new one.")

def select_portions_fzf(portions, select, prompt):
    if len(portions) > 1:
        if indices:=iterator_fzf_select(portions, fzf_process(["--multi", "--prompt", prompt])):
            for i in indices:
                select.select_by_visible_text(portions[i])
                yield portions[i]
    else:
        logger.info(f"only one portion ({portions[0]}) was present.")
        yield portions[0]

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
    WebDriverWait(driver, 10).until(EC.invisibility_of_element((By.ID, "floatingCirclesG")))
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
    all_indices=[]
    callback = lambda _, name_url: name_urls.append((name_url[0], name_url[1]))
    process = fzf_process()
    def search_all_types(query):
        for type in ("Foundation","SR Legacy"):
            try:
                yield from search(query, type)
            except TimeoutException:
                pass
    if indices:=iterator_fzf_select(search_all_types(query), process, callback, to_str):
        all_indices+=indices

    process.terminate()
    process.wait()
    return [name_urls[i] for i in all_indices]

def fzf_process(args=["--multi"]):
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
    import time
    driver.get(f"https://fdc.nal.usda.gov/food-search?type={type}&query={query}")
    selector = By.CSS_SELECTOR, "app-food-search>div>div>div>div>table>tbody>tr"
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    elements = None
    count = 0

    while count < 50:
        new_elements = driver.find_elements(*selector)
        if elements is None:
            elements = new_elements
        else:
            if elements == new_elements:
                count+=1
                time.sleep(0.1)
                continue
            else:
                elements = new_elements
                count = 50
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
    from datetime import datetime
    from pathlib import Path
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kroot")

    parser = ArgumentParser(prog='kroot', description='(pronounced carrot) a script for you to gather data about food you eat')
    parser.add_argument('--search', type=str, help="search food in the USDA's database")
    parser.add_argument('--add', help="interactively add nom nom-ed food", action="store_true")
    parser.add_argument('--foodsfile', type=FileType("r+"), default=str(Path.home().joinpath(".config/kroot/foods.csv")))
    parser.add_argument('--atedir', type=Path, default=Path.home().joinpath(".config/kroot/ate/"))
    args = parser.parse_args()
    main(args)
