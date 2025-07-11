import asyncio
import pandas as pd
import json
import os
import re
import requests
import random
from p_logging import get_logger

Category_dir = "Top_Categories"
if not os.path.exists(Category_dir):
    os.makedirs(Category_dir) 

log_file_path = os.path.join(Category_dir, "Top_Categories.log")
logger = get_logger('top_categories_logger', log_file_path)

logger.info("This will go ONLY to Top_Categories.log")

log_file_path = "Top_Categories/Top_Categories.log"

# logger = logger.getLogger()
# logger.setLevel(logger.INFO)

# Avoid adding multiple handlers if script is run multiple times
if not logger.handlers:
    # File handler
    file_handler = logger.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logger.INFO)
    file_formatter = logger.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Stream handler (console)
    stream_handler = logger.StreamHandler()
    stream_handler.setLevel(logger.INFO)
    stream_handler.setFormatter(file_formatter)
    logger.addHandler(stream_handler)

output_dir = "Top_Categories/best_selling_products_images"
# logo_dir = "Top_Categories/category_logo"
trend_dir = "Top_Categories/trend_images"
os.makedirs(output_dir, exist_ok=True)
# os.makedirs(logo_dir, exist_ok=True)
os.makedirs(trend_dir, exist_ok=True)

# GLOBALS TO TRACK COUNTERS ACROSS PAGES
image_counter = 1
logo_counter = 1
trend_counter = 1
rank_counter = 1

async def extract_category_data(page, page_num):
    global image_counter, logo_counter, trend_counter

    # Base index starts at 1 for page 1, 51 for page 2, 101 for page 3, etc.
    global image_counter, logo_counter, trend_counter, rank_counter

    # Base index starts at 1 for page 1, 51 for page 2, 101 for page 3, etc.
    base_index = 1 + (page_num - 1) * 10
    image_counter = logo_counter = trend_counter = rank_counter = base_index

    # Continue with the rest of your scraping logic...
    logger.info(f"Scraping page {page_num}...")

    await page.wait_for_selector(".ant-table-row", timeout=10000)

    rows = await page.query_selector_all(".ant-table-row")
    logger.info(f"Loaded {len(rows)} categories")

    all_categories = []
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.kalodata.com"
    }

    for index, row in enumerate(rows):
        # ✅ Shop Logo
        row_key = await row.get_attribute("data-row-key") or "N/A"

        # Category Name
        category_name_el = await row.query_selector("div.font-medium.hover\\:text-kalo-primary")
        category_name = await category_name_el.inner_text() if category_name_el else "N/A"

        # Revenue
        rev_el = await row.query_selector("td.ant-table-cell.ant-table-column-sort")
        rev_text = await rev_el.inner_text() if rev_el else "N/A"

        # All TDs (for trend screenshots)
        td_elements = await row.query_selector_all("td")

        rev_growth_rate = await td_elements[4].inner_text() if len(td_elements) > 4 else "N/A"
        num_shops = await td_elements[6].inner_text() if len(td_elements) > 6 else "N/A"
        rev_per_shops = await td_elements[7].inner_text() if len(td_elements) > 7 else "N/A"
        category_lvl = await td_elements[8].inner_text() if len(td_elements) > 8 else "N/A"
        top3_shops_ratio = await td_elements[9].inner_text() if len(td_elements) > 9 else "N/A"
        top10_shops_ratio = await td_elements[10].inner_text() if len(td_elements) > 10 else "N/A"

        # Revenue Trend Screenshot
        revenue_trend_filename = "N/A"
        if len(td_elements) > 5:
            try:
                revenue_trend_filename = f"revenue_trend_{row_key}.png"
                await td_elements[5].screenshot(path=os.path.join(trend_dir, revenue_trend_filename))
                logger.info(f"Screenshot saved for revenue trend: {revenue_trend_filename}")
            except Exception as e:
                logger.error(f"Error capturing screenshot for revenue trend: {e}")

        # Best Seller Images
        best_seller_ids = []
        best_seller_images = []
        product_elements = ""
        all_product_names = []
        price_elements = ""
        all_product_prices = []
        image_divs = await row.query_selector_all("div.Component-Image.cover.cover")
        for image_div in image_divs:
            try:
                if await image_div.is_visible():
                    await image_div.scroll_into_view_if_needed()
                    await image_div.hover()
                    await asyncio.sleep(0.2)
                    # await asyncio.sleep(random.uniform(0.2, 0.5))
                    logger.info(f"Hovered over image div {image_counter}")
                    # await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Error scrolling into view for image div {image_counter}: {e}")

            # Image URL
            style = await image_div.get_attribute("style")
            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if match:
                url = match.group(1)
                id_match = re.search(r'tiktok\.product/(\d+)/', url)
                product_id = id_match.group(1) if id_match else None
                try:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        image_name = f"shop_{product_id}_image_{image_counter}.png"
                        image_path = os.path.join(output_dir, image_name)
                        with open(image_path, "wb") as f:
                            f.write(response.content)
                        best_seller_images.append(image_name)
                        best_seller_ids.append(product_id)  # ✅ Save product ID
                        logger.info(f"Saved {image_name} with product ID {product_id}")
                        # logger.info(f"Saved {image_name}")
                        image_counter += 1
                    else:
                        logger.info(f"Failed to download image (status {response.status_code})")
                except Exception as e:
                    logger.error(f"Error downloading {url}: {e}")
        await rev_el.hover()
        # await asyncio.sleep(0.1)
        await asyncio.sleep(0.2)
        # Best Seller Product Names (collected like a shared pool)
        product_elements = await page.query_selector_all("span.line-clamp-2")
        all_product_names = []
        for p in product_elements:
            product_name = await p.inner_text()
            # normalized_product_name = ' '.join(product_name.split())
            # if normalized_product_name not in all_product_names:
            all_product_names.append(' '.join(product_name.split()))
        all_product_prices = []
        # Best Seller Prices (similarly, as shared pool)
        price_elements = await page.query_selector_all("div.text-\\[16px\\].min-w-\\[80px\\].h-\\[20px\\].font-medium.bg-white")
        for el in price_elements:
            price_text = await el.inner_text()
            # normalized_price = ' '.join(price_text.split())
            # if normalized_price not in all_product_prices:
            all_product_prices.append(price_text)

        category_data = {
            "Row Key": row_key,
            "Rank": rank_counter,
            "Category Name": category_name,
            "Best Seller IDs": best_seller_ids,
            "Best Sellers": [],  # filled later
            "Best Seller Prices": [],  # filled later
            "Best Seller Images": best_seller_images,
            "Revenue": rev_text,
            "Revenue Growth Rate": rev_growth_rate,
            "Revenue Trend": revenue_trend_filename,
            "Number of Shops": num_shops,
            "Revenue per Shop": rev_per_shops,
            "Category Level": category_lvl,
            "Top 3 Shops Ratio": top3_shops_ratio,
            "Top 10 Shops Ratio": top10_shops_ratio
        }

        all_categories.append(category_data)
        trend_counter += 1
        rank_counter += 1

        product_idx = 0
        for prod in all_categories:
            num_images = len(prod["Best Seller Images"])
            prod["Best Sellers"] = all_product_names[product_idx:product_idx + num_images]
            # shop["Best Seller Prices"] = all_product_prices[product_idx:product_idx + num_images]
            product_idx += num_images
                    
        # Assign Best Seller Prices based on Best Sellers
        price_idx = 0
        for prod in all_categories:
            num_products = len(prod["Best Sellers"])
            prod["Best Seller Prices"] = all_product_prices[price_idx:price_idx + num_products]
            price_idx += num_products
        
        # Display results
        for i, shop in enumerate(all_categories):
            logger.info(f"\nCategory {i + 1}:")
            for k, v in shop.items():
                print(f"  {k}: {v if not isinstance(v, list) else ', '.join(v)}")        
    
    return all_categories

async def run_category_scraper(page, page_num):
    logger.info("Starting scraper...")
    try:
        if page_num == 1 or page_num == 4 or page_num == 7:
            logger.info("Clicking 'Category' link inside #page_header_left...")
            await page.click("#page_header_left >> text=Category")

            await page.click("span.ant-select-selection-item")
            await page.wait_for_selector("div.ant-select-item-option-content")
            options = await page.query_selector_all("div.ant-select-item-option-content")
            for option in options:
                text = await option.inner_text()
                if "50 / page" in text:
                    await option.click()
                    break

            await page.click("div.h-\\[22px\\].hover\\:bg-\\[rgb\\(238\\,246\\,253\\)\\].rounded-\\[4px\\].pl-\\[4px\\].flex.items-center.justify-between.text-\\[13px\\].whitespace-nowrap")
            await page.get_by_text("Last 7 Days").click()
            await page.click("span.animate-pulse-subtle")

        await asyncio.sleep(2)
        
        all_results = []
        semaphore = asyncio.Semaphore(5)  # Limit concurrent page processing

        async def process_page(page_num):
            nonlocal all_results
            async with semaphore:
                try:
                    # if page_num > 1:
                    #     selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("{page_num}")'
                    #     try:
                    #         await page.click(selector)
                    #         await asyncio.sleep(3)
                    #     except Exception as e:
                    #         logger.error(f"Page {page_num} navigation failed: {e}")
                    #         return

                    if page_num > 1:
                        selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("{page_num}")'
                        if page_num == 4:
                            selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("5")'
                            await page.click(selector)
                            await asyncio.sleep(3)
                            selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("{page_num}")'
                        elif page_num == 7:
                            selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("5")'
                            await page.click(selector)
                            selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("7")'
                            await page.click(selector)
                            await asyncio.sleep(3)
                            selector = f'li.ant-pagination-item >> a[rel="nofollow"]:has-text("{page_num}")'
                        try:
                            if selector:
                                await page.click(selector)
                                await asyncio.sleep(3)
                            else:
                                more = await page.query_selector("span.ant-pagination-item-ellipsis")
                                await page.click(more)
                                
                        except Exception as e:
                            logger.error(f"Page {page_num} navigation failed: {e}")
                            await page.click("span.ant-pagination-item-ellipsis")
                            await page.click(selector)
                            await asyncio.sleep(3)
                            return

                    page_results = await extract_category_data(page, page_num)
                    all_results.extend(page_results)

                    # Save progressively
                    allcategory = pd.DataFrame(page_results)
        
                    # Save to CSV
                    df = pd.DataFrame(allcategory)
                    df["Row Key"] = df["Row Key"].apply(lambda x: f"'{x}")
                    df["Best Sellers"] = df["Best Sellers"].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
                    df["Best Seller Prices"] = df["Best Seller Prices"].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
                    df["Best Seller Images"] = df["Best Seller Images"].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
                    
                    # Use a lock for file operations
                    async with asyncio.Lock():
                        df.to_csv("Top_Categories/top_categories_output.csv", mode="a", index=False, 
                                 header=not os.path.exists("Top_Categories/top_categories_output.csv"))
                        with open("Top_Categories/top_categories_output.json", "a", encoding="utf-8") as f:
                            json.dump(page_results, f, ensure_ascii=False, indent=4)

                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}")
                    if "TargetClosedError" in str(e):
                        raise  # Re-raise if page was closed

        # # Create tasks for all pages but process them with limited concurrency
        # tasks = [process_page(page_num) for page_num in range(1, 11)]
        # await asyncio.gather(*tasks, return_exceptions=True)
        # for page_num in range(1, 11):
        #     await process_page(page_num)
        await process_page(page_num)

        logger.info("Scraping complete!")
        logger.info(f"Total categories scraped: {len(all_results)}")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise

    logger.info("Scraping complete!")
    logger.info(f"Total categories scraped: {len(all_results)}")

async def category_main(page, page_range):
    # for page_num in range(1,2):
    #     await run_category_scraper(page, page_num)  # You can loop this later if needed
    for page_num in page_range:
        await run_category_scraper(page, page_num)  # You can loop this later if needed
    await page.close()
