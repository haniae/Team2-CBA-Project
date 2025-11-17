# ⚡ Quick Test Guide - Interactive Forecasting

**Use this for rapid testing before demos**

---

## 🚀 **Quick Start (30 seconds)**

```bash
# Terminal 1: Start server
cd /home/malcolm-munoriyarwa/projects/Team2-CBA-Project
python -m finanlyzeos_chatbot.web

# Terminal 2: Watch logs (optional)
tail -f logs/app.log

# Browser: Open UI
http://localhost:8000
```

---

## ✅ **5-Minute Smoke Test**

### **Test 1: Basic Forecast (30 sec)**
```
Query: "Forecast Tesla revenue using LSTM"
Expected: Forecast + exploration prompts
✅ Check: See "💡 Want to explore further?" section
```

### **Test 2: Follow-Up - Why? (30 sec)**
```
Query: "Why is it increasing?"
Expected: Driver breakdown with 📈📊📉 emojis
✅ Check: See feature importance or components
```

### **Test 3: Follow-Up - Confidence (30 sec)**
```
Query: "How confident are you?"
Expected: Confidence intervals + explanation
✅ Check: See "95% CI" ranges for each year
```

### **Test 4: Save Forecast (30 sec)**
```
Query: "Save this as Tesla_Test"
Expected: ✅ Confirmation message
✅ Check: See "You can reference it later"
```

### **Test 5: Compare (30 sec)**
```
Query: "Compare to Tesla_Test"
Expected: Side-by-side comparison table
✅ Check: See Year | Baseline | Current | Delta columns
```

---

## 🧪 **Extended Test Suite (15 minutes)**

### **Scenario Testing**
```
1. "Forecast Apple revenue"
2. "What if marketing spend increases 15%?"
3. "What if COGS rises 5%?"
4. "What if volume grows 20%?"

✅ Check: Qualitative impact analysis provided
```

### **Model Switching**
```
1. "Forecast Microsoft revenue using LSTM"
2. "Switch to Prophet"
3. "Switch to ARIMA"

✅ Check: Acknowledgment + model comparison
```

### **Parameter Adjustment**
```
1. "Forecast Google revenue"
2. "Change horizon to 5 years"
3. "Exclude 2020 as outlier"

✅ Check: Parameter change acknowledged
```

### **Edge Cases**
```
1. "Why?" (without forecast) → Should explain no active forecast
2. "Compare to NonExistent" → Should list available forecasts
3. "Save this" (without forecast) → Should request forecast first
4. Generic pronoun: "Explain it" → Should reference active forecast

✅ Check: Graceful error messages, no crashes
```

---

## 🐛 **Common Issues & Fixes**

### **Issue: "No active forecast" error**
**Cause:** Forecast metadata not stored  
**Fix:** Run forecast query again, check logs for storage confirmation

### **Issue: Follow-up doesn't understand context**
**Cause:** Follow-up detection not matching  
**Fix:** Check `_detect_forecast_followup` patterns in chatbot.py

### **Issue: Explainability data is empty**
**Cause:** Model didn't return explainability  
**Fix:** Check if model supports explainability (LSTM, Prophet have best support)

### **Issue: Comparison says "Not found"**
**Cause:** Forecast wasn't actually saved  
**Fix:** Verify save confirmation message appeared first

---

## 📊 **Expected Response Patterns**

### **✅ Good Forecast Response:**
- Shows predicted values with confidence intervals
- Includes model details (architecture, training loss, etc.)
- Ends with "💡 Want to explore further?" section
- Lists 5+ exploration options

### **✅ Good Explainability Response:**
- Has emoji headers (📈📊📉)
- Lists specific drivers with percentages/values
- Explains business impact for each driver
- Maintains conversational tone

### **✅ Good Confidence Response:**
- Shows confidence intervals per year
- Explains interval width meaning
- Includes model confidence percentage
- Transparent about limitations

### **✅ Good Save Confirmation:**
- Starts with ✅ emoji
- Confirms exact saved name
- Provides reference examples
- Asks about next steps

### **✅ Good Comparison Response:**
- Markdown table format
- Year | Baseline | Current | Delta columns
- Explains key differences
- Provides insights on trade-offs

---

## 🎯 **Judge Demo Checklist**

**Before Demo:**
- [ ] Server running and responsive
- [ ] Browser cache cleared
- [ ] Database has data (check size > 0 bytes)
- [ ] Practiced script 2-3 times
- [ ] Have backup scenarios ready

**During Demo:**
- [ ] Start with simple forecast
- [ ] Show automatic exploration prompts
- [ ] Do ONE follow-up (Why?)
- [ ] Save the forecast
- [ ] Compare if time allows
- [ ] Keep explanations brief

**After Demo:**
- [ ] Thank judges
- [ ] Offer technical Q&A
- [ ] Highlight judge feedback incorporation
- [ ] Provide GitHub/documentation links

---

## 💡 **Pro Tips**

1. **Use Tesla for demos** - Most recognizable company
2. **Revenue is safest metric** - Most reliable data
3. **LSTM shows best** - Most technical, best explainability
4. **"Why?" is most impressive** - Shows context preservation
5. **Keep it under 5 minutes** - Attention spans are short

---

## 🚨 **Emergency Fallbacks**

### **If Forecast Fails:**
> "The ML models need historical data. Let me explain the architecture instead..."
[Show architecture diagram]

### **If Follow-Up Breaks:**
> "The forecast state is still propagating. Let me regenerate and try again..."
[Rerun original forecast]

### **If Everything Breaks:**
> "The system is under active development. Let me walk you through the code and show what we've built..."
[Open chatbot.py, show follow-up detection]

**Remember:** Judges appreciate honesty + deep understanding over perfect demos.

---

## 📝 **Quick Testing Commands**

```bash
# Check if server is running
curl http://localhost:8000/health

# Check database size
ls -lh data/finanlyzeos.db

# Check logs for errors
tail -n 50 logs/app.log | grep ERROR

# Restart server fresh
pkill -f "finanlyzeos_chatbot.web"
python -m finanlyzeos_chatbot.web

# Clear browser cache
Ctrl+Shift+Delete (Chrome/Firefox)
```

---

## ✅ **Success Criteria**

Your implementation is working if:
- ✅ Forecast generates with exploration prompts
- ✅ "Why?" provides detailed drivers
- ✅ "How confident?" shows intervals
- ✅ Save/compare works within same session
- ✅ No crashes or exceptions

**If 4/5 work, you're demo-ready!** 🚀

---

## 📞 **Need Help?**

**Documentation:**
- Technical: `INTERACTIVE_FORECASTING_IMPLEMENTATION.md`
- Demo Script: `INTERACTIVE_FORECASTING_DEMO_SCRIPT.md`
- Full Summary: `SESSION_SUMMARY.md`

**Code References:**
- Follow-up detection: `chatbot.py` lines 4797-4878
- Context building: `chatbot.py` lines 4880-5242
- State management: `chatbot.py` lines 524-600
- Explainability: `context_builder.py` lines 1875-1927

**Logs to Check:**
- Application: `logs/app.log`
- Server console: Terminal output
- Browser console: F12 → Console tab

---

**You've got this! Go make the judges impressed! 🎯🚀**

