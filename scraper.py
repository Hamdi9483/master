import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

def extract_and_sync_live_currencies():
    # قراءة مفاتيح الاتصال من بيئة العمل السحابية (GitHub Actions Secrets)
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Error in Supabase Keys ")

    # إنشاء اتصال العميل مع Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    url = "https://sp-today.com/currencies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    extracted_data = []
    
    try:
        print(" start bringing data form sp-today...")
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # استخراج كافة النصوص مرتبة حسب ظهورها في الصفحة
            page_text = soup.get_text(separator="\n")
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            
            # استخراج ديناميكي كامل بالترتيب يبدأ من الدولار وباقي العملات
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # التحقق إذا كان السطر يمثل اسماً محتملاً لعملة أو مادة (قصير وليس رقماً)
                if not any(char.isdigit() for char in line) and 2 <= len(line) < 35:
                    if i + 2 < len(lines):
                        p1 = lines[i + 1]
                        p3 = lines[i + 3]
                        
                        # التأكد من أن الأسطر اللاحقة هي أسعار رقمية حية
                        if (any(char.isdigit() for char in p1) and len(p1) < 15 and
                            any(char.isdigit() for char in p3) and len(p3) < 15):
                            
                            extracted_data.append([line, p1, p3])
                            i += 3
                            continue
                i += 1

        # تصفية البيانات لمنع التكرار مع الحفاظ على الترتيب الحقيقي
        unique_data = []
        seen = set()
        valid_keywords = ["دولار", "يورو", "ليرة", "ريال", "درهم", "دينار", "جنيه", "استرليني", "ذهب", "أونصة"]

        for item in extracted_data:
            name = item[0]
            if name not in seen and any(kw in name for kw in valid_keywords):
                seen.add(name)
                unique_data.append(item)

        if not unique_data:
            print(" Warning No data has brought.")
            return

        # تجهيز البيانات للإرسال دفعة واحدة إلى Supabase
        records_to_insert = []
        for item in unique_data:
            records_to_insert.append({
                "currency_name": item[0],
                "sell_price": item[1],
                "buy_price": item[2]
            })

        print(f" Data Uploaded to Supabase...")
        
        # تنفيذ عملية الإدخال في جدول currency_rates
        response_db = supabase.table('currency_rates').insert(records_to_insert).execute()
        
        print(" senocronize data to Supabase successfully !")

    except Exception as e:
        print(f" Error during scraping or database connection: {e}")
        raise e

if __name__ == "__main__":
    extract_and_sync_live_currencies()