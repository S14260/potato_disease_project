import requests


API_KEY = "50292894f8b4218d1d0b96581337944d"


def get_weather(city):

    try:

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}"
            f"&appid={API_KEY}"
            f"&units=metric"
            f"&lang=zh_cn"
        )

        response = requests.get(url)

        data = response.json()

        print("🌦 天气API返回：", data)

        # =========================
        # 温度
        # =========================

        temperature = data["main"]["temp"]

        # =========================
        # 湿度
        # =========================

        humidity = data["main"]["humidity"]

        # =========================
        # 天气描述
        # =========================

        weather_text = data["weather"][0][
            "description"
        ]

        # =========================
        # 是否降雨
        # =========================

        rainfall = False

        if "雨" in weather_text:

            rainfall = True

        return {

            "temperature": temperature,

            "humidity": humidity,

            "weather": weather_text,

            "rainfall": rainfall

        }

    except Exception as e:

        print("❌ 天气API错误:", e)

        # fallback
        return {

            "temperature": 20,

            "humidity": 70,

            "weather": "未知",

            "rainfall": False

        }