from ai.llm_agent import generate_advice

label = "Potato Late Blight"

environment = {
    "temperature": 28,
    "humidity": 50,
    "rainfall":False
}

result = generate_advice(label, environment)

print(result)