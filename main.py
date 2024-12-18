#!/usr/bin/env python3

def main(args):
    with args.foodsfile as foodsfile:
        if query:=args.search:
            if args.firefox:
                firefox_driver(args.browser_args)
            else:
                chrome_driver(args.browser_args)
            search_food_write_csv(query, foodsfile)
        try:
            if args.add:
                add_from_foods_to_today_file(foodsfile)
            if food_name:=args.compose:
                compose_foods_write_to_csv(food_name, foodsfile)
            if args.compare:
                compare_foods_matplot(foodsfile)
        except KeyboardInterrupt:
            print()
            logger.info("interrupt. quitting...")
            exit(1)

def compare_foods_matplot(foodsfile):
    import csv
    rows = list(csv.DictReader(foodsfile))
    to_str = lambda i, item: f"{i}. {item['Name']} ({item['Portion']})\n"
    if indices:=iterator_fzf_select(rows, fzf_process(['--multi', "--prompt", f"Select foods to compare> "]), to_str=to_str):
        selected = {i:rows[i] for i in indices}
        imax, max_calorie = max(selected.items(), key=lambda ix: float(ix[1]["Energy"]))
        key_max = len(max(max_calorie, key=len))
        pad_max = len(max_calorie["Name"])
        for i, row in selected.items():
            if i != imax:
                print(" "*(key_max+1), max_calorie["Name"],"   ", row["Name"])
                coefficient = float(max_calorie["Energy"])/float(row["Energy"])
                print(f"{(key_max-8)*" "} Serving: {"1".ljust(pad_max+5," ")}{coefficient:.3f}")
                for key, item in row.items():
                    try:
                        item = float(item)*coefficient
                        print(f"{key.rjust(key_max)}: {"{:.3f}".format(float(max_calorie[key])).ljust(pad_max+5, " ")}{item:.3f}")
                    except ValueError as e:
                        continue

def compose_foods_write_to_csv(food_name, foodsfile):
    import csv
    rows = list(csv.DictReader(foodsfile))
    to_str = lambda i, item: f"{i}. {item['Name']} ({item['Portion']})\n"
    if indices:=iterator_fzf_select(rows, fzf_process(['--multi', "--prompt", f"Select foods to compose into \"{food_name}\"> "]), to_str=to_str):
        def is_ok(key):
            try:
                float(rows[0][key])
                return True
            except ValueError:
                return False
        amount_per_portion = {i: get_amount_from_stdin(rows[i], prompt=f"How much {rows[i]['Name']} ({rows[i]['Portion']}) is used per portion?")
                              for i in indices}
        item = {key: sum(float(rows[i][key])*amount_per_portion[i]
                         for i in indices)
                for key in rows[0].keys()
                if is_ok(key)}
        item["Portion"] = input("What's the portion for this food?\n> ")
        item["Name"] = food_name
        writer = csv.DictWriter(foodsfile, rows[0].keys())
        writer.writerow(item)
        logger.info(f"wrote \"{food_name}\" to csv file successfully.")

def add_from_foods_to_today_file(foodsfile):
    import csv
    rows = list(csv.DictReader(foodsfile))
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
                item["Amount"] = get_amount_from_stdin(item)
                writer.writerow(item)
                logger.info(f"wrote to file {path}")


def get_amount_from_stdin(item, prompt=None):
    if prompt is None:
        prompt = f"How much of \"{item['Name']} ({item['Portion']})\" you consumed (float)?"
    print(prompt, end="\n> ")
    while True:
        try:
            s = input()
            return float(s)
        except ValueError:
            print(end="> ")


def search_food_write_csv(query, foodsfile):
    import csv
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
            logger.info(f"reading data of \"{name}\" ({portion}) ...")
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
    element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(selector))
    select = Select(element)
    return tuple(map(attrgetter("text"), select.options)), select

def get_keys(keys, units={}):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    WebDriverWait(driver, 10).until(EC.invisibility_of_element((By.ID, "floatingCirclesG")))
    selector = By.CSS_SELECTOR, "app-food-nutrients>div>div>table>tbody>tr:nth-child(-n+10)"
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    for item in driver.find_elements(*selector):
        try:
            name, value, unit = take(3, map(lambda x: x.text.strip(), item.find_elements(By.XPATH,".//td")))
        except ValueError:
            continue
        try:
            unit_ok = units[name] == unit
        except KeyError:
            unit_ok = True
        if unit_ok and (key:=next((key for key in keys if key in name or key.lower() in name), None)) is not None:
            try:
                yield key, float(value), unit
            except ValueError:
                continue
            try:
                yield key, float(value[1:]), unit
            except ValueError:
                continue

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
    from selenium.common.exceptions import StaleElementReferenceException
    import time
    logger.debug("getting")
    driver.get(f"https://fdc.nal.usda.gov/food-search?type={type}&query={query}")
    selector = By.CSS_SELECTOR, "app-food-search>div>div>div>div>table>tbody>tr"
    logger.debug("waiting")
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    elements = None
    count = 0

    logger.debug("whiling")
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
        logger.debug("inside whiling")
        while i < len(elements):
            try:
                element = elements[i]
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

def chrome_driver(args):
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver import ChromeOptions, Chrome
    global driver
    options = ChromeOptions()
    service = Service("/sbin/chromedriver")
    if args:
        for arg in args:
            options.add_argument(arg)
    else:
        options.add_argument("--headless=new")

    driver = Chrome(options=options, service=service)

def firefox_driver(args):
    from selenium.webdriver import FirefoxOptions, Firefox
    global driver
    options = FirefoxOptions()
    if args:
        for arg in args:
            options.add_argument(arg)
    else:
        options.add_argument("-headless")
    driver = Firefox(options=options)

def take(n, iterable):
    from itertools import islice
    return list(islice(iterable, n))

if __name__ == "__main__":
    from argparse import ArgumentParser, FileType
    from datetime import datetime
    from pathlib import Path
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kroot")
    from sys import argv

    parser = ArgumentParser(prog='kroot', description='(pronounced carrot) a script for you to gather data about food you eat')
    parser.add_argument('--search', type=str, help="search food in the USDA's database")
    parser.add_argument('--add', help="interactively add nom nom-ed food", action="store_true",default=len(argv) == 1)
    parser.add_argument('--foodsfile', type=FileType("r+"), default=str(Path.home().joinpath(".config/kroot/foods.csv")))
    parser.add_argument('--atedir', type=Path, default=Path.home().joinpath(".config/kroot/ate/"))
    parser.add_argument('--compose', help="are you beethoven? cuz your composed food's so delicious.")
    parser.add_argument('--compare', help="compare foods together", action="store_true")
    parser.add_argument('--firefox', help="use foxy driver for scraping", action="store_true")
    parser.add_argument('--browser-args', help="browser arguments (headless if non present)", action="append")
    args = parser.parse_args()
    main(args)
