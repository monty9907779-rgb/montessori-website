# 🌿 Montessori Nursery Finance App
## Complete Setup & Deployment Guide

---

## STEP 1 — Install Required Software (Do This Once)

### Install Node.js
1. Go to: https://nodejs.org
2. Download the **LTS version** (the green button)
3. Install it — click Next through all steps
4. To verify: open Terminal (Mac) or Command Prompt (Windows) and type:
   ```
   node --version
   ```
   You should see something like: `v20.11.0`

---

## STEP 2 — Set Up the Project

1. **Save the project folder** `montessori-nursery` somewhere easy (e.g. your Desktop)

2. **Open Terminal / Command Prompt** and navigate to the folder:
   ```bash
   cd Desktop/montessori-nursery
   ```

3. **Install dependencies:**
   ```bash
   npm install
   ```
   This takes 2-3 minutes. You'll see packages being downloaded.

4. **Run locally to test:**
   ```bash
   npm start
   ```
   Your browser will open at http://localhost:3000
   
   **Login credentials:**
   - Director: `director@montessori.com` / `director123`
   - Finance Manager: `finance@montessori.com` / `finance123`

---

## STEP 3 — Build for Production

```bash
npm run build
```

This creates a `build/` folder with optimized files ready to deploy.

---

## STEP 4 — Deploy Online (FREE — Vercel)

### Option A: Vercel (Easiest — Recommended)

1. Go to https://vercel.com and create a free account
2. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```
3. Deploy:
   ```bash
   vercel
   ```
4. Follow the prompts — answer Yes to all defaults
5. Your app will be live at: `https://montessori-nursery.vercel.app`

### Option B: Netlify (Also Free)

1. Go to https://netlify.com and create a free account
2. Drag and drop your `build/` folder onto the Netlify dashboard
3. Done! You get a URL like: `https://montessori-nursery.netlify.app`

---

## STEP 5 — Install as Mobile App (No App Store Needed!)

This makes the app feel exactly like a native app on phones.

### On iPhone:
1. Open Safari (must be Safari, not Chrome)
2. Go to your app URL
3. Tap the **Share button** (box with arrow at bottom)
4. Scroll down → tap **"Add to Home Screen"**
5. Tap **"Add"**
6. The app icon appears on your home screen! 🎉

### On Android:
1. Open Chrome
2. Go to your app URL
3. Tap the **three dots menu** (top right)
4. Tap **"Add to Home Screen"**
5. Tap **"Install"**
6. Done! 🎉

Both the Finance Manager and Director can install it this way.

---

## STEP 6 — Use a Custom Domain (Optional)

If you want `finance.montessori.com` instead of a Vercel URL:

1. Buy a domain at: https://namecheap.com (~$10/year)
2. In Vercel dashboard → Settings → Domains → Add your domain
3. Follow their DNS instructions (takes ~24 hours to activate)

---

## 🔄 Upgrading to a Real Database (Future Step)

Currently the app stores data in the browser's local storage.
This means data is per-device. To sync across devices:

**Recommended: Supabase (Free)**
1. Sign up at https://supabase.com
2. Create a new project
3. Contact a developer to connect the app — costs ~2-4 hours of work
4. All data then syncs between all users in real-time

---

## 📱 App Store (Native App — Optional)

To publish on Apple App Store or Google Play Store:

| Step | Details |
|------|---------|
| Apple Developer Account | $99/year at developer.apple.com |
| Google Developer Account | $25 one-time at play.google.com/console |
| Convert to native app | Use Capacitor.js (free) or hire a developer |
| Submit for review | Apple takes 1-3 days, Google takes 1-3 days |

**The PWA (Step 5) is usually sufficient** for a small nursery team.
It installs on phones, works offline, and avoids App Store fees.

---

## 🔑 User Accounts

Current accounts (change passwords after first login):

| User | Email | Password | Access |
|------|-------|----------|--------|
| Director (You) | director@montessori.com | director123 | Full access |
| Finance Manager | finance@montessori.com | finance123 | Full access |

To add more users: edit `src/utils/database.js` and add to the `users` array in `seedDatabase()`.

---

## 📞 Support

If you get stuck at any step, the commands to remember are:
```bash
npm install     # Set up the project
npm start       # Run locally for testing
npm run build   # Prepare for deployment
vercel          # Deploy online
```

---

*Built for Montessori Nursery — Finance Management System v1.0*
