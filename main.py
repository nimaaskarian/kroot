

def main():
    from argparse import ArgumentParser, FileType
    parser = ArgumentParser(prog='havij', description='a script for you to gather data about food you eat')
    parser.add_argument('--search', type=str)
    parser.add_argument('--foodsfile', type=FileType("r+"), default="/home/nima/.config/havij/foods.csv")
    args = parser.parse_args()
    if query:=args.search:
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver import ChromeOptions, Chrome
        from more_itertools import take
        import csv
        global driver
        options = ChromeOptions()
        service = Service("/sbin/chromedriver")
        options.add_argument("--headless=new")
        driver = Chrome(options=options, service=service)
        keys = [ "Energy", "Protein", "Carbohydrate", "Sugar" ]
        units = {
                "Energy": "kcal"
                }
        if (name_url := prompt_url_fzf(query)):
            name, url = name_url
            writer = csv.writer(args.foodsfile)
            csv_dict_reader = csv.DictReader(args.foodsfile)
            portions, select = get_portions_element(url)
            portions = list(portions)
            if len(portions) > 1:
                portion = set_portion_fzf(portions, select)
            else:
                portion = portions[0]
            row = {key: value for key, value, _ in take(len(keys), get_keys(keys, units))}
            row["Name"] = name
            row["Portion"] = portion
            for key in keys:
                if not (item:=row.get(key,0)):
                    row[key] = item
            writer = csv.DictWriter(args.foodsfile, ["Name", "Portion"]+keys, lineterminator="\n")
            if not any(csv_dict_reader):
                writer.writeheader()
            writer.writerow(row)
            args.foodsfile.close()

def set_portion_fzf(portions, select):
    if i:=iterator_fzf_select(portions):
        select.select_by_visible_text(portions[i])
        return portions[i]

def get_portions_element(url):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.select import Select
    driver.get(url)
    selector = By.ID, "nutrient-per-selection-Survey-or-branded"
    element = WebDriverWait(driver, 2).until(EC.presence_of_element_located(selector))
    select = Select(element)
    return (item.text for item in select.options), select
    # for item in select.options: yield item.text


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
    to_str = lambda i, name_url_cat: f"{i}. \"{name_url_cat[0]}\" in \"{name_url_cat[2]}\"\n"
    name_urls = []
    callback = lambda _, name_url: name_urls.append((name_url[0], name_url[1]))
    if i:=iterator_fzf_select(search(query), callback, to_str):
        return name_urls[i]

def iterator_fzf_select(iterator, callback=None, to_str=lambda i, item: f"{i}. {item}\n"):
    import subprocess
    process = subprocess.Popen(
            "fzf",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
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
    if output:=process.stdout.read():
        return int(output[:output.index(".")])

def search(query):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver import ActionChains
    from selenium.common.exceptions import StaleElementReferenceException
    driver.get(f"https://fdc.nal.usda.gov/food-search?type=Foundation&query={query}")
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
            except ValueError:
                continue
            url = url_name.find_element(By.CSS_SELECTOR,"a").get_attribute("href")
            yield url_name.text, url, category.text
            i+=1
        except StaleElementReferenceException:
            elements = driver.find_elements(*selector)

if __name__ == "__main__":
    main()
