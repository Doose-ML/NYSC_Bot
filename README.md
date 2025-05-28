# NYSC Camp Assistant Bot 🎖️🤖

*A smart Telegram assistant for Nigerian Youth Service Corps members, providing instant answers to camp-related questions and 24/7 support.*

## 🌟 What This Bot Does

This bot helps NYSC members navigate camp life by:
- **Answering FAQs** about call-up letters, allowances, camp requirements, and redeployment
- **Providing official information** from the NYSC portal in real-time
- **Logging unanswered questions** for admin response
- **Sending important updates** about schedule changes or announcements

## 🔥 Key Features

### 🗂️ Comprehensive Knowledge Base
- Instant replies to 50+ common questions
- Fuzzy matching for similar questions (e.g., "callup" → "call-up letter")
- Covers all camp phases: pre-mobilization, orientation, and post-camp

### ⚡ Smart Automation
- Auto-updates FAQs from Google Sheets every 6 hours
- Saves new Q&A pairs to Firebase after admin approval
- Sends notifications when questions get answered

### 🔒 Secure Access
- Admin-only commands for managing content
- All sensitive data stored in environment variables
- Firebase rules restrict unauthorized database access

### 🌐 Always Online
- 24/7 hosting via Replit + UptimeRobot
- Built-in Flask server prevents downtime
- Lightweight design (uses only ~150MB RAM)

## 📚 Information Categories
1. **Pre-Camp**  
   - Call-up letters  
   - Registration requirements  
   - What to bring  

2. **Camp Life**  
   - Daily schedule  
   - Dress code  
   - Mammy market info  

3. **Post-Camp**  
   - PPA posting  
   - Allowance payments  
   - Redeployment process  

