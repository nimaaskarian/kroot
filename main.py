

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
            row = {key: value for key, value, _ in take(len(keys), get_keys(keys, url, units))}
            keys.insert(0, "Name")
            row["Name"] = name
            for key in keys:
                if not (item:=row.get(key,0)):
                    row[key] = item
            writer = csv.DictWriter(args.foodsfile, keys)
            if not any(csv_dict_reader):
                writer.writeheader()
            writer.writerow(row)
            args.foodsfile.close()

def get_keys(keys, url, units={}):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    driver.get(url)
    from selenium.webdriver.common.by import By
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
    urls = []
    try:
        for i, (name, url, category) in enumerate(search(query)):
            process.stdin.write(f"{i}. \"{name}\" in \"{category}\"\n")
            process.stdin.flush()
            urls.append((name,url))
        process.stdin.close()
    except BrokenPipeError:
        pass
    if output:=process.stdout.read():
        index = int(output[:output.index(".")])
        return urls[index]
    return None

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
