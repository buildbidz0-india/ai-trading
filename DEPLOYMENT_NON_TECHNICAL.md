# Simple Deployment Guide (For Everyone)

Welcome! This guide will help you put your Trading Platform on the internet. You don't need to be a computer expert. We will use a service called **Vercel**, which makes this very easy.

---

## 🐣 What is Vercel?
Think of **Vercel** as a "home" for your website.
- **GitHub** (where code lives) is like a blueprint.
- **Vercel** takes that blueprint and builds the house for you instantly.

---

## 📝 Step 1: Create Accounts (The Keys to the House)

Before we start, you need to sign up for these services. They are free to start.

1.  **GitHub**: Go to [github.com](https://github.com) and create an account.
2.  **Vercel**: Go to [vercel.com](https://vercel.com) and sign up using your **GitHub** account.
3.  **Google AI / Gemini**: Get your API keys from Google AI Studio. **Get at least 3 keys** if possible (this helps the app run smoother).

---

## ☁️ Step 2: Upload Your Code

1.  Go to **GitHub** and create a new repository (repo). Name it `trading-platform`.
2.  On your computer, if you downloaded the code folder:
    -   Go to the folder.
    -   "Push" the code to your new GitHub repository. (If you don't know how to do this, ask a developer friend to "push the code to GitHub" for you).

---

## 🚀 Step 3: Deployment (Putting it Online)

We will deploy the **Backend** (the brain) and the **Frontend** (the face) separately.

### Part A: Deploy the Backend (The Brain)

1.  Go to your **Vercel Dashboard**.
2.  Click **"Add New..."** -> **"Project"**.
3.  You will see your `trading-platform` repo. Click **Import**.
4.  **Important**:
    -   Change **Root Directory** to `backend`. (Click "Edit" next to Root Directory and select the `backend` folder).
5.  **Environment Variables** (The Secret Passwords):
    -   Open the "Environment Variables" section.
    -   You need to add your keys here.
    -   **Name**: `GOOGLE_API_KEYS`
    -   **Value**: Paste your keys separated by commas.
        -   *Correct*: `key1,key2,key3`
        -   *Incorrect*: `key1 key2`
    -   Add other keys (`OPENAI_API_KEY`, etc.) if you have them.
6.  Click **Deploy**.
7.  Wait for it to finish. You will get a link (e.g., `https://trading-backend.vercel.app`). **Copy this link.**

### Part B: Deploy the Frontend (The Face)

1.  Go back to **Vercel Dashboard**.
2.  Click **"Add New..."** -> **"Project"**.
3.  Import the **SAME** `trading-platform` repo again.
4.  **Important**:
    -   Change **Root Directory** to `frontend`.
5.  **Environment Variables**:
    -   **Name**: `NEXT_PUBLIC_API_URL`
    -   **Value**: Paste the link you copied from Part A (e.g., `https://trading-backend.vercel.app`).
        -   *Note*: Remove the trailing slash `/` at the end if there is one.
6.  Click **Deploy**.

---

## 🎉 Step 4: You Are Live!

Click the image of your website in Vercel. You should see your platform running!

### 🛑 Troubleshooting (If things break)
-   **"500 Error"**: Check your API keys. Did you put commas between them?
-   **"Network Error"**: Check `NEXT_PUBLIC_API_URL`. Did you paste the Backend URL correctly?

Enjoy your new AI Trading Platform! 🚀
