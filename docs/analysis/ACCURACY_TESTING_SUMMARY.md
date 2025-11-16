# 📊 BenchmarkOS Chatbot Accuracy Testing: Executive Summary

**Date**: November 12, 2025  
**Framework**: NIST Measurement Trees (arXiv:2509.26632)  
**Status**: Plan Complete, Ready to Execute

---

## 🎯 What We're Testing

The BenchmarkOS financial chatbot's **accuracy, validity, and reliability** across 4 key dimensions:

1. **Factual Accuracy** (FA): Can it retrieve correct financial data?
2. **Financial Reasoning** (FR): Can it analyze trends and make comparisons?
3. **Data Integrity** (DI): Does it cite sources and avoid hallucinations?
4. **User Experience** (UX): Is it helpful, clear, and trustworthy?

---

## 🌳 Measurement Tree Framework

### Why Measurement Trees?

Traditional AI metrics give you a single score (like "92% accuracy"). **Measurement trees** give you a **hierarchical view** that shows:

- **Overall Score** (Level 1): Is the system production-ready?
- **Dimension Scores** (Level 2): Which areas are strong/weak?
- **Construct Scores** (Level 3-4): What specific issues exist?
- **Individual Data** (Level 5): Exact test cases that failed

**Key Innovation**: Uses **maximum** (worst-case) aggregation at top level, so critical failures bubble up immediately.

### Our 5-Level Tree

```
Level 1: Overall Chatbot Accuracy (0-10 risk score)
    ├─ Level 2: Factual Accuracy Testing
    │   ├─ Level 3: Automated Checks
    │   │   ├─ Level 4: FA-1 (Numerical Accuracy)
    │   │   │   └─ Level 5: [Test case: "Apple revenue FY2024"]
    │   │   ├─ Level 4: FA-3 (Growth Calculations) ⚠️ PERCENTAGE BUG
    │   │   │   └─ Level 5: [Test case: "Apple YoY growth 2024"]
    │   │   └─ ...
    │
    ├─ Level 2: Financial Reasoning Testing
    │   ├─ Level 3: Expert Annotations
    │   │   ├─ Level 4: FR-1 (Trend Analysis)
    │   │   └─ ...
    │   └─ Level 3: User Perceptions
    │       └─ ...
    │
    ├─ Level 2: Field Testing (Real Users)
    │   └─ ...
    │
    └─ Level 2: Red Teaming (Adversarial)
        ├─ Level 3: Expert Annotations
        │   ├─ Level 4: RB-1 (Guardrails)
        │   ├─ Level 4: DI-3 (Hallucination Resistance)
        │   └─ ...
        └─ ...
```

---

## 🧪 Testing Phases

### Phase 1: Automated Testing (Week 1-2)
**Method**: Python scripts + database ground truth  
**Volume**: 100+ test queries  
**Cost**: $500 infrastructure + 40 hours engineering  

**What We Test**:
- ✅ Can bot retrieve Apple's FY2024 revenue correctly?
- ✅ Can bot calculate YoY growth without astronomical percentage bug?
- ✅ Can bot handle multiple metrics in one query?

**Success Criteria**: FA-1, FA-3 risk scores ≤ 2.0

---

### Phase 2: Expert Evaluation (Week 2-3)
**Method**: 3-5 financial analysts annotate multi-turn conversations  
**Volume**: 15 scenarios × 3-5 turns each = 45-75 responses  
**Cost**: $6,000 (5 analysts × 8 hours × $150/hr)

**What We Test**:
- ✅ Does bot correctly analyze Apple's profitability trends?
- ✅ Does bot make valid comparisons between companies?
- ✅ Does bot maintain context across conversation turns?

**Success Criteria**: FR-1 through FR-5 risk scores ≤ 3.0

---

### Phase 3: Field Testing (Week 3-4)
**Method**: 15-20 finance professionals use the bot freely  
**Volume**: 200+ real user queries  
**Cost**: $2,000 (20 users × $100 gift card)

**What We Test**:
- ✅ Do users find responses helpful?
- ✅ Do users trust the information?
- ✅ Would users use this in their actual work?

**Success Criteria**: UX-1 through UX-5 risk scores ≤ 4.0

---

### Phase 4: Red Teaming (Week 4-5)
**Method**: 5-10 engineers try to break the system  
**Volume**: 75+ adversarial prompts  
**Cost**: $5,000 (10 engineers × 5 hours × $100/hr)

**What We Test**:
- ✅ Can bot resist hallucination triggers?
- ✅ Do guardrails block investment advice requests?
- ✅ Can bot handle jailbreak attempts?

**Success Criteria**: RB-1, DI-3 risk scores ≤ 2.0 (critical!)

---

## 📈 Risk Scoring System

### 0-10 Scale (Higher = More Risk)

| Score | Level | Meaning | Action |
|-------|-------|---------|--------|
| **0-2** | ✅ Excellent | Production-ready | Ship it! |
| **3-4** | ⚠️ Good | Minor issues | Quick fixes, then ship |
| **5-6** | ⚠️ Moderate | Needs work | Improve before production |
| **7-8** | ❌ Poor | Major problems | Don't ship yet |
| **9-10** | 🚨 Critical | Severely broken | Urgent fixes required |

### Critical Constructs (Cannot Fail)

These MUST have risk ≤ 2.0 for production:

- **FA-1**: Numerical accuracy (revenue, income, margins)
- **FA-3**: Growth calculations (YoY, CAGR) ← **Percentage bug here!**
- **DI-3**: No hallucinations (making up data)
- **RB-1**: Guardrails (refusing investment advice)
- **UX-5**: User trust

If any of these fail, **system is not production-ready**.

---

## 🐛 Known Issues to Address

Based on recent debugging:

### 🚨 CRITICAL (Must Fix Before Testing)

**1. Astronomical Percentage Bug** (FA-3, DI-5)
```
Query: "How did Apple's revenue grow in 2024?"
❌ Current: "391035000000.0%" 
✅ Expected: "2.1%"
```
**Status**: Fixed with post-processor in `chatbot.py:1752-1806`  
**Verify**: Run Test Set B (growth calculations)

**2. Hallucination When No Data** (DI-3)
```
Query: "What was XYZ Corp's revenue?"
❌ Current: Makes up numbers
✅ Expected: "I don't have data for XYZ Corp"
```
**Status**: Partially fixed in `context_builder.py:3761-3779`  
**Verify**: Query non-existent companies

---

### ⚠️ HIGH PRIORITY

**3. Source Attribution Missing** (DI-1)
- Responses should include "📊 **Sources:**" with links
- Currently unknown if this works consistently

**4. Context Loss in Multi-Turn** (DQ-1)
- Bot should remember "Apple" from Turn 1 in Turn 2
- Not yet tested

---

### 📊 MODERATE

**5. Response Formatting** (UX-2)
- User reported "formatting looks bad"
- Needs visual inspection by experts

---

## 💰 Budget Summary

### Full Testing (6 weeks)
- Expert panel: **$6,000**
- Field testing: **$2,000**
- Red teaming: **$5,000**
- Test development: **$4,000**
- Analysis/reporting: **$4,000**
- Infrastructure: **$800**

**Total: ~$21,800**

### Pilot Testing (3 weeks, reduced scope)
- Skip external experts (use internal): Save $6,000
- 10 field testers instead of 20: Save $1,000
- 3 red teamers instead of 10: Save $3,500

**Pilot Total: ~$11,300**

---

## ✅ Quick Start: Test NOW (5 minutes)

### Step 1: Ensure Server is Running
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok", ...}
```

### Step 2: Run Automated Tests
```bash
cd /home/malcolm-munoriyarwa/projects/Team2-CBA-Project
source .venv/bin/activate
python tests/test_accuracy_automated.py
```

### Step 3: Check Risk Score
```
==================================================================================
Overall Risk Score: 2.1/10 - Good (minor issues) ✅
==================================================================================
```

**If score > 2.0**: Review `critical_failures` and fix bugs before continuing.

---

## 📝 Deliverables

After completing all phases, you'll receive:

### 1. Measurement Tree Visualization
- Interactive HTML showing all 5 levels
- Color-coded risk scores (green/yellow/orange/red)
- Drill-down to individual test failures

### 2. Executive Summary (1-page)
- Overall risk score with recommendation
- Top 5 strengths and weaknesses
- Production readiness: **Go / No-Go**

### 3. Technical Deep-Dive (20-30 pages)
- Full methodology
- Results by construct with examples
- Root cause analysis for failures
- Prioritized improvement roadmap

### 4. Test Results Database
- JSON file with all 500+ test results
- Queryable by construct, dimension, test case
- Includes chatbot transcripts for failed cases

---

## 🎯 Success Criteria for Production

**Overall**: Risk score ≤ 3.0  
**No Level 2 dimension**: Risk > 5.0  
**Critical constructs** (FA-1, FA-3, DI-3, RB-1, UX-5): All ≤ 2.0

If these are met → **Ship to production** ✅  
If not → **Iterate and re-test** ❌

---

## 📚 Documentation Files

Created for you:

1. **`ACCURACY_TEST_PLAN.md`** (Full 50-page plan)
   - Complete methodology
   - All test queries
   - Scoring rubrics
   - 6-week roadmap

2. **`TESTING_QUICKSTART.md`** (Quick 5-minute guide)
   - Run tests now
   - Check percentage bug
   - Troubleshooting

3. **`tests/test_accuracy_automated.py`** (Executable script)
   - Automated test runner
   - Risk score calculator
   - JSON report generator

4. **`arxiv_2509_26632.pdf`** (NIST paper)
   - Original research paper
   - Measurement tree theory
   - CoRIx case study

---

## 🚀 Next Actions

### Immediate (Today)
1. ✅ Review this summary
2. ✅ Run quick automated test: `python tests/test_accuracy_automated.py`
3. ✅ Verify percentage bug is fixed (FA-3 score ≤ 2.0)

### Short-Term (This Week)
4. ✅ Fix any critical failures from automated tests
5. ✅ Read `ACCURACY_TEST_PLAN.md` for full details
6. ✅ Decide: Full testing ($21.8k) or Pilot ($11.3k)?

### Medium-Term (Next 6 Weeks)
7. ✅ Execute testing phases 1-4
8. ✅ Generate measurement tree visualization
9. ✅ Receive production readiness recommendation

---

## 🤝 Questions?

- **Methodology**: See `ACCURACY_TEST_PLAN.md` Section 1-3
- **Test Queries**: See `ACCURACY_TEST_PLAN.md` Section 4
- **Quick Testing**: See `TESTING_QUICKSTART.md`
- **Paper Details**: See `arxiv_2509_26632.pdf`

---

**Bottom Line**: This plan gives you a **systematic, evidence-based** way to evaluate your chatbot using a **NIST-approved framework**. It will definitively tell you if the system is production-ready, and if not, exactly what needs to be fixed.

The percentage bug can be tested **today** in 5 minutes. The full evaluation takes 6 weeks and $22k (or 3 weeks and $11k for pilot).

**Ready to test?** Start with `TESTING_QUICKSTART.md` 🚀

