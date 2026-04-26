# 🌱 Karsh.Ai — AI-Powered Farming Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-black?style=for-the-badge&logo=ollama&logoColor=white" />
  <img src="https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" />
</p>

**Karsh.Ai** is an intelligent agricultural dashboard designed to empower rural farmers by bridging the technology gap. It provides data-driven insights, personalized government scheme recommendations, and real-time alerts to ensure sustainable farming and financial security.

### 🌐 Live Demo: [karshai-for-farmers.streamlit.app](https://karshai-for-farmers.streamlit.app/)

---

## 🚀 Key Features

### 🏛️ Government Scheme Finder
- **Personalized Matching:** Enter your annual income and landholding size to find eligible central and state government schemes.
- **Smart Filtering:** Categorizes schemes into subsidies, loans, and direct benefits.
- **Up-to-date Data:** Powered by a comprehensive database of agricultural incentives.

### 🌱 Precision Crop Predictor
- **Location-Based Insights:** Suggests the best crops to plant based on your specific district in Kerala.
- **Economic Forecasting:** Estimates potential earnings and provides planting schedules based on the current month and land size.
- **Machine Learning Powered:** Uses historical data to predict optimal crop yields.

### 💬 Malayalam Chatbot
- **Multilingual Support:** Interact with the dashboard in English or Malayalam.
- **Expert Advice:** Ask questions about fertilizers, irrigation, or disease control.
- **Fast Responses:** Powered by Groq (Llama 3.3) for near-instant answers.

### 📸 AI Plant Identifier
- **Disease Detection:** Upload photos of your crops to identify pests or diseases instantly.
- **Expert Recommendations:** Get immediate advice on treatment and preventive measures based on image analysis.

### ⚠️ Early Warning System
- **Weather Forecasting:** Provides a detailed 48-hour outlook for your district.
- **Calamity Alerts:** Real-time warnings for extreme rain, wind, or heatwaves that could affect your harvest.

---

## 🛠️ Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/) (for a fast, interactive web interface)
- **AI/LLM:** [Groq](https://groq.com/) & [Gemini](https://aistudio.google.com/) (for high-speed intelligent query handling)
- **ML Models:** Scikit-Learn (for crop prediction algorithms)
- **Natural Language:** `gTTS` & `deep-translator` (for Malayalam support)
- **Data Handling:** Pandas & JSON
- **Styling:** Custom CSS with Glassmorphism aesthetics

---

## 📦 Installation

To run Karsh.Ai locally, follow these steps:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/SRDxRestricted/Karsh.Ai
   cd Karsh.Ai
   ```

2. **Set up Virtual Environment:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   uv sync
   # OR
   pip install -r requirements.txt
   ```

4. **Configure API Keys:**
   - Create a folder named `.streamlit` in the root directory.
   - Create a file named `secrets.toml` inside that folder.
   - Add your API keys (Groq is recommended for higher limits):
     ```toml
     GROQ_API_KEY = "your_groq_key_here"
     GEMINI_API_KEY = "your_gemini_key_here"
     ```
   - *Note: This file is already in .gitignore and will not be pushed to GitHub.*

5. **Run the Application:**
   ```bash
   streamlit run app.py
   ```

---

## 📂 Project Structure

```text
├── app.py                  # Main landing page & Dashboard
├── auth.py                 # User authentication logic
├── theme.py                # UI/UX design tokens & Global CSS
├── pages/                  # Multipage Streamlit application
│   ├── 1_Malayalam_Chatbot.py
│   ├── 2_Crop_Predictor.py
│   ├── 3_Govt_Scheme_Finder.py
│   └── 4_Plant_Identifier.py
├── scheme_recommender/     # Logic & Data for govt schemes
├── early_warning_system/   # Weather monitoring & Alerts
├── imageProcessing/        # Plant disease identification logic
└── Malayalam TTS/          # Voice processing assets
```

---

## 🤝 Contributing

We welcome contributions from the community! Whether it's adding new schemes, improving the ML models, or translating to more languages:
1. Fork the repo.
2. Create a new branch.
3. Commit your changes.
4. Open a Pull Request.

---

## 🏆 Team Xenonites404
Built with ❤️ for the farming community. 

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.