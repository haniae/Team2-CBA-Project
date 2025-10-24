# CFI Dashboard - User Guide

## 🚀 Quick Start Guide

Welcome to the enhanced CFI Financial Dashboard! This guide will help you make the most of the new features.

---

## 🎨 Theme & Display Options

### **Dark Mode**
Switch between light and dark themes for comfortable viewing in any environment.

**How to use:**
- Click the **sun/moon icon** in the top toolbar
- Or press **`D`** on your keyboard
- Your preference is automatically saved

**Benefits:**
- Reduced eye strain in low-light
- Better battery life on OLED screens
- Professional appearance

---

### **Density Controls**
Choose how much information you want to see at once.

**Three modes available:**

1. **Comfortable** 📊 - Spacious view with generous padding
2. **Compact** 📈 - Balanced default view (recommended)
3. **Dense** 📉 - Maximum data density for power users

**How to use:**
- Click the **density icons** in the top toolbar
- Each icon shows a preview of the layout

---

### **Currency Selector**
View financial data in your preferred currency.

**Supported currencies:**
- 💵 USD (US Dollar)
- 💶 EUR (Euro)
- 💷 GBP (British Pound)

**How to use:**
- Click the **currency symbol** buttons in the toolbar
- Data will be converted in real-time (in future versions)

---

## 🔍 Search & Navigation

### **Smart Search**
Find any metric quickly with fuzzy matching.

**How to use:**
1. Click the search box or press **`/`**
2. Start typing (e.g., "rev" finds "Revenue")
3. Matching items are highlighted in yellow
4. Panels with matches get a colored border

**Features:**
- Searches across all metrics
- Fuzzy matching (finds partial matches)
- Search history saved (last 10 searches)
- Real-time results

---

### **Deep Linking**
Share specific views with colleagues.

**URL Parameters:**
- `?section=keyfin` - Jump to Key Financials
- `?metric=revenue` - Search and highlight Revenue
- `?section=kpi&metric=ebitda` - Combine parameters

**Example:**
```
https://dashboard.com/cfi?section=keyfin&metric=ebitda
```

---

## ⌨️ Keyboard Shortcuts

Master the dashboard with these quick shortcuts:

| Key | Action |
|-----|--------|
| `/` | Focus search box |
| `R` | Refresh dashboard |
| `E` | Open export menu |
| `D` | Toggle dark/light mode |
| `Esc` | Close any modal |
| `1-6` | Toggle KPI category 1-6 |
| `?` | Show this shortcuts list |

**Pro tip:** All shortcuts work from anywhere on the page!

---

## 📊 Enhanced Data Visualization

### **Sparklines**
Mini charts in KPI cards show trends at a glance.

**What they show:**
- ✅ Green line = Positive trend
- ❌ Red line = Negative trend
- • Blue dot = Latest value
- 📈 Area fill = Historical range

**Auto-generated** from your time series data!

---

### **Cross-Panel Highlighting**
See related data across the dashboard.

**How it works:**
1. Hover over any KPI card
2. Related metrics in tables light up
3. Move mouse away to clear

**Great for:** Comparing metrics across different time periods

---

## 📥 Export & Sharing

### **Print Dashboard**
Create printer-friendly reports.

**How to print:**
1. Press `Ctrl+P` (Windows) or `Cmd+P` (Mac)
2. Dashboard auto-adjusts for printing:
   - Removes buttons and toolbars
   - Expands all collapsed sections
   - Optimizes for A4/Letter paper
   - Preserves all charts

---

### **Offline Access**
The dashboard works even without internet!

**Offline features:**
- View last loaded data
- Navigate between sections
- Use search and filters
- Export to PDF/Excel

**How it works:**
- First visit caches the dashboard
- Subsequent visits load from cache
- Updates automatically when online

**Status:** Look for the green dot in the toolbar

---

## 🔔 Notifications

Stay informed with toast notifications.

**Types:**
- ✅ **Success** - Green, operations completed
- ℹ️ **Info** - Blue, helpful information
- ⚠️ **Error** - Red, something went wrong

**Auto-dismiss** after 4 seconds or click **×** to close immediately.

---

## 📱 Mobile & Touch

### **Touch-Friendly**
All buttons are optimized for fingers (min 44px).

**Mobile features:**
- Swipe-friendly panels
- Large touch targets
- No hover-required actions
- Mobile-optimized search

---

### **Back to Top**
Quickly return to the dashboard header.

**How to use:**
- Scroll down past 300 pixels
- Blue button appears in bottom-right
- Click to smoothly scroll to top

---

## ♿ Accessibility Features

### **Keyboard Navigation**
Navigate the entire dashboard without a mouse.

**How to use:**
1. Press `Tab` to move between elements
2. Press `Enter` or `Space` to activate
3. Press `Shift+Tab` to go back

**Focus indicators:** Blue outline shows where you are

---

### **Screen Readers**
Fully compatible with NVDA, JAWS, and VoiceOver.

**Features:**
- All images have alt text
- Buttons have descriptive labels
- Charts have text alternatives
- Skip to content link at top

---

### **Reduced Motion**
Respects your system preferences.

**If motion reduction is enabled:**
- Animations are instant (0.01ms)
- No distracting effects
- Smoother experience

**How to enable:**
- Windows: Settings → Ease of Access → Display
- Mac: System Preferences → Accessibility → Display
- Dashboard auto-detects your preference

---

## 🎯 Pro Tips

### **1. Multi-Select KPIs**
Use `Shift+Click` to select multiple KPIs for comparison.

### **2. Quick Export**
Press `E` then `1/2/3` for PDF/PPTX/Excel respectively.

### **3. Search History**
Your last 10 searches are saved. Press Up/Down in search box to navigate.

### **4. Density for Presentations**
- **Comfortable** for client presentations
- **Compact** for daily analysis
- **Dense** for screenshot reports

### **5. Theme Switching**
Match your company brand:
- Light mode for public reports
- Dark mode for internal analysis

---

## 🔧 Troubleshooting

### **Dashboard won't load**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh (Ctrl+F5)
3. Check network connection
4. Try incognito/private mode

### **Theme won't save**
- Enable cookies/local storage in browser
- Check if browser is in private mode
- Update to latest browser version

### **Offline mode not working**
- Visit dashboard once while online
- Wait for "Service Worker registered" in console
- Check if HTTPS is enabled (required for Service Workers)

### **Charts not displaying**
- Enable JavaScript
- Check if Plotly.js loaded (look for errors in console)
- Refresh page

### **Keyboard shortcuts not working**
- Click anywhere on dashboard first
- Check if another app is using the same shortcut
- Try without browser extensions

---

## 📞 Getting Help

### **Keyboard Shortcuts Help**
Press **`?`** anytime to see the shortcuts overlay.

### **Data Freshness**
Check the **green/yellow/red dot** in toolbar:
- 🟢 Green = Updated < 5 minutes ago
- 🟡 Yellow = Updated 5-30 minutes ago
- 🔴 Red = Updated > 30 minutes ago

### **Console Logs**
For developers: Open Console (F12) to see:
- Service Worker status
- Cache hits/misses
- API call logs
- Error messages

---

## 🎓 Learning Path

### **Beginner (Day 1)**
1. ✅ Toggle dark mode
2. ✅ Try different density views
3. ✅ Use search to find metrics
4. ✅ Explore keyboard shortcuts (press ?)

### **Intermediate (Week 1)**
1. ✅ Set up your preferred theme & density
2. ✅ Learn all keyboard shortcuts
3. ✅ Use cross-panel highlighting
4. ✅ Export your first report

### **Advanced (Month 1)**
1. ✅ Create shareable deep links
2. ✅ Use search history effectively
3. ✅ Master density switching for presentations
4. ✅ Teach colleagues the power features

---

## 📊 Feature Comparison

| Feature | Old Dashboard | New Dashboard |
|---------|---------------|---------------|
| Dark Mode | ❌ No | ✅ Yes |
| Keyboard Nav | ⚠️ Basic | ✅ Complete |
| Offline Support | ❌ No | ✅ Yes |
| Search | ⚠️ Browser only | ✅ Smart fuzzy search |
| Mobile Optimized | ⚠️ Partial | ✅ Full |
| Print Support | ⚠️ Basic | ✅ Optimized |
| Accessibility | ⚠️ Partial | ✅ WCAG AA |
| Sparklines | ❌ No | ✅ Yes |
| Themes | 1 | 2 |
| Density Options | 1 | 3 |

---

## 🎉 Welcome aboard!

You're now ready to make the most of the CFI Dashboard. Explore, experiment, and discover what works best for your workflow.

**Need more help?** Press `?` for quick shortcuts or check the comprehensive documentation.

**Happy analyzing! 📈**

---

*Last updated: October 24, 2025*  
*Version: 2.0*

