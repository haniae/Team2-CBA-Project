# How to Test Your Chatbot Without Pushing

## 🧪 Three Ways to Test

### Method 1: Quick Test (Fastest - 5 queries)
```bash
python test_chatbot_queries.py --quick
```
Tests 5 key queries to verify basic functionality works.

### Method 2: Comprehensive Test (Recommended - 30+ queries)
```bash
python test_chatbot_queries.py
```
Tests queries across all categories and provides a detailed report.

### Method 3: Interactive Testing (Best for Manual Verification)
```bash
python test_chatbot_interactive.py
```
Allows you to:
- Test queries one by one
- See full responses
- Type your own queries
- Use 'test' command for predefined queries
- Type 'quit' to exit

---

## ✅ What Gets Tested

### Query Categories:
1. **Simple & Direct** - "apple revenue", "tesla margins"
2. **With Typos** - "microsft revenu", "appl margens"
3. **Conversational** - "how's apple doing", "what's up with tesla"
4. **Comparisons** - "apple vs microsoft", "which is better"
5. **Why Questions** - "why did tesla margins drop"
6. **Forecasting** - "forecast apple revenue", "nvidia outlook"
7. **Complex Multi-Part** - Long queries with multiple parts
8. **Unrelated Queries** - "what's the weather", "tell me a joke"
9. **Financial Concepts** - "what is revenue", "explain margins"
10. **Edge Cases** - Empty strings, gibberish, punctuation

---

## 📊 What to Look For

### Good Response Indicators:
- ✅ Response length: 50+ characters (meaningful content)
- ✅ No error messages ("I don't understand", "I cannot", etc.)
- ✅ Answers the question directly
- ✅ Provides helpful information
- ✅ Uses proper financial terminology when relevant

### Warning Signs:
- ⚠️ Response too short (< 50 chars)
- ⚠️ Contains error indicators
- ⚠️ Generic/unhelpful responses
- ⚠️ Crashes or exceptions

---

## 🚀 Quick Start

1. **Run quick test first:**
   ```bash
   python test_chatbot_queries.py --quick
   ```
   Should complete in 1-2 minutes.

2. **If quick test passes, run comprehensive:**
   ```bash
   python test_chatbot_queries.py
   ```
   Takes 5-10 minutes, tests all categories.

3. **For manual verification:**
   ```bash
   python test_chatbot_interactive.py
   ```
   Then:
   - Type `test` to run predefined queries
   - Type your own queries
   - Type `quit` to exit

---

## 📝 Sample Test Session

```bash
# Start interactive testing
python test_chatbot_interactive.py

# In the interactive session:
> test                    # Runs "apple revenue"
> test                    # Runs "microsft revenu" (typo)
> test                    # Runs "how's apple doing"
> apple vs microsoft      # Your own query
> why did tesla margins drop
> what's the weather       # Unrelated query
> quit                    # Exit
```

---

## 🎯 Success Criteria

Your chatbot is working well if:
- ✅ 90%+ queries get helpful responses
- ✅ No crashes or exceptions
- ✅ Typos are corrected automatically
- ✅ Complex queries are handled
- ✅ Unrelated queries get helpful responses (not errors)
- ✅ Responses are meaningful (50+ chars)

---

## 🔧 Troubleshooting

### If tests fail to initialize:
- Check database path in settings
- Verify database exists
- Check LLM API keys are set

### If responses are poor:
- Check LLM API is working
- Verify context is being built
- Check system prompt is loaded

### If typos aren't corrected:
- Verify alias_builder.py changes are in place
- Check fuzzy matching is enabled

---

## 💡 Tips

1. **Start with quick test** - Fastest way to verify basic functionality
2. **Use interactive mode** - Best for understanding what's happening
3. **Test edge cases** - Unrelated queries, typos, empty strings
4. **Check response quality** - Not just that it responds, but that it's helpful
5. **Test conversation flow** - Try follow-up questions

---

**Happy Testing! 🚀**

