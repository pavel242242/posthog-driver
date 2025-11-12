# 🚀 Start Here - Claude Agent SDK + PostHog Integration

## What You Asked: "How could this use Claude Agent SDK?"

**Answer:** You have 3 working examples + complete documentation. Here's your guide.

---

## ⚡ Quick Start (5 minutes)

### 1. Set API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export E2B_API_KEY="e2b_..."
export POSTHOG_API_KEY="phx_..."
export POSTHOG_PROJECT_ID="12345"
```

### 2. Run Example

```bash
# Simplest example (100 lines)
python3 minimal_claude_example.py

# Full conversational agent (350 lines)
python3 claude_agent_with_posthog.py

# E2B demo without Claude
python3 quick_start_e2b.py
```

### 3. See It Work

```
💬 User: What are the top events?

🤖 Claude: I'll use the query_posthog tool

🔍 Executing in E2B sandbox...

🤖 Claude: Here are the top 5 events:
1. $pageview - 1,521 events from 243 users
2. user_logged_in - 507 events from 87 users
...
```

---

## 📚 Documentation (Pick Your Path)

### Path 1: I Want to Learn (15 minutes)

1. **CLAUDE_SDK_SUMMARY.md** ← **START HERE**
   - Complete answer to "how could this use Claude Agent SDK?"
   - 3 integration methods explained
   - Examples with expected output
   - Common questions answered

2. **ARCHITECTURE_CLAUDE.md**
   - Visual diagrams of how it works
   - Message flow timeline
   - Component interactions
   - Security & performance details

3. **CLAUDE_INTEGRATION.md**
   - Deep dive into integration
   - Code patterns explained
   - Troubleshooting guide
   - Production checklist

### Path 2: I Want to Build (30 minutes)

1. **minimal_claude_example.py**
   - Read the code (100 lines)
   - Understand the 3-step pattern
   - Run it yourself
   - Modify for your needs

2. **claude_agent_with_posthog.py**
   - Read the full implementation
   - See conversation loop
   - Understand tool execution
   - Test with different questions

3. **agent_executor.py** + **script_templates.py**
   - Reusable production components
   - Pre-built query templates
   - Sandbox lifecycle management
   - Error handling patterns

### Path 3: I Just Want It to Work (5 minutes)

1. **GET_STARTED.md**
   - 3-step quick start
   - Copy-paste commands
   - See immediate results
   - No deep understanding needed

2. **quick_start_e2b.py**
   - Ready-to-run script
   - Pre-configured example
   - Automatic setup
   - Shows expected output

---

## 🗂️ File Guide

### 🎯 Want to understand Claude integration?
→ **CLAUDE_SDK_SUMMARY.md** (this is your main answer)

### 🏗️ Want to see architecture?
→ **ARCHITECTURE_CLAUDE.md** (visual diagrams)

### 📖 Want detailed docs?
→ **CLAUDE_INTEGRATION.md** (complete guide)

### 💻 Want runnable code?
→ **minimal_claude_example.py** (simplest)
→ **claude_agent_with_posthog.py** (complete)

### 🚀 Want to demo quickly?
→ **quick_start_e2b.py** (E2B only)
→ **GET_STARTED.md** (3-step guide)

### 📊 Want to see real analysis?
→ **ANALYSIS_RESULTS.md** (real PostHog data analyzed)
→ **live_analysis.py** (how it was generated)

### 🧪 Want to see all features?
→ **show_demo.py** (interactive demo)

### 📝 Want complete API docs?
→ **README.md** (full documentation)

### 🏢 Want production components?
→ **agent_executor.py** (sandbox manager)
→ **script_templates.py** (query templates)
→ **examples/persona_workflows.py** (10 use cases)

### 🔧 Want to understand the driver?
→ **posthog_driver/client.py** (core implementation)

---

## 🎓 Learning Path

### Beginner (Never used Claude tools)

1. Read **CLAUDE_SDK_SUMMARY.md** sections:
   - "The Answer: 3 Integration Methods"
   - "How The Integration Works"
   - "Quick Start"

2. Run:
   ```bash
   python3 minimal_claude_example.py
   ```

3. Read the code in **minimal_claude_example.py**

4. Understand the 3 steps:
   - Define tool
   - Call Claude with tool
   - Execute tool when requested

### Intermediate (Used Claude tools before)

1. Read **ARCHITECTURE_CLAUDE.md** sections:
   - "Complete System Architecture"
   - "Message Flow Timeline"

2. Run:
   ```bash
   python3 claude_agent_with_posthog.py
   ```

3. Study these functions:
   - `question_to_query()` - NLP to HogQL
   - `execute_posthog_query_in_e2b()` - E2B execution
   - `execute_posthog_tool()` - Tool handler
   - `run_claude_agent()` - Message loop

4. Modify for your use case

### Advanced (Building production app)

1. Read **CLAUDE_INTEGRATION.md** sections:
   - "Extending the Integration"
   - "Production Checklist"

2. Study production components:
   - **agent_executor.py** - Sandbox lifecycle
   - **script_templates.py** - Reusable templates

3. Implement:
   - Error handling
   - Rate limiting
   - Caching
   - Monitoring

4. Deploy with proper auth and secrets management

---

## 🔍 Common Questions

### Q: How does Claude know about PostHog?
**A:** You define a tool that tells Claude what it can do:
```python
TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics...",
    "input_schema": {...}
}
```

### Q: How does the query actually run?
**A:** Your code receives Claude's tool request and executes it in E2B:
```python
if response.stop_reason == "tool_use":
    result = execute_in_sandbox(sandbox, tool_use.input)
```

### Q: Why E2B sandboxes?
**A:** Security & isolation:
- ✅ Can't access your local files
- ✅ Can't modify your system
- ✅ Automatic cleanup
- ✅ Same environment every time

### Q: Can I use this without E2B?
**A:** Yes, but not recommended for production. See **examples/basic_usage.py**

### Q: Can I use this without Claude?
**A:** Yes! The driver works standalone. See **quick_start_e2b.py**

### Q: What can Claude do with this?
**A:** Answer questions like:
- "What are the top events?"
- "Where do users drop off?"
- "Who are the power users?"
- "What drives conversion?"
- "Show me the funnel"

### Q: Can I add more tools?
**A:** Yes! Define additional tools for:
- Exporting cohorts
- Creating insights
- Tracking events
- Managing feature flags

---

## 📊 Examples by Use Case

### Use Case: Analytics Dashboard
**Files:** claude_agent_with_posthog.py, script_templates.py
**Pattern:** Conversational queries, formatted results

### Use Case: Data Export
**Files:** agent_executor.py, TEMPLATES['export_events']
**Pattern:** Bulk data extraction

### Use Case: User Segmentation
**Files:** examples/persona_workflows.py (Customer Success)
**Pattern:** Cohort identification and export

### Use Case: Conversion Analysis
**Files:** live_analysis.py, ANALYSIS_RESULTS.md
**Pattern:** Funnel analysis, drop-off identification

### Use Case: Power User Detection
**Files:** script_templates.py (identify_power_users)
**Pattern:** Activity-based segmentation

---

## 🎯 Next Steps

### If you're new to this:
1. ✅ Read **CLAUDE_SDK_SUMMARY.md**
2. ✅ Run **minimal_claude_example.py**
3. ✅ Understand the 3-step pattern
4. ✅ Modify for your questions

### If you want to build something:
1. ✅ Copy **claude_agent_with_posthog.py**
2. ✅ Customize `QUERY_TEMPLATES`
3. ✅ Add your own tool definitions
4. ✅ Build a UI on top

### If you want production-ready:
1. ✅ Use **agent_executor.py**
2. ✅ Leverage **script_templates.py**
3. ✅ Add error handling
4. ✅ Implement monitoring
5. ✅ Read **CLAUDE_INTEGRATION.md** production section

---

## 🆘 Troubleshooting

### "Missing API key"
→ Check environment variables are set
→ See section 1 of Quick Start above

### "Sandbox creation failed"
→ Verify E2B API key at https://e2b.dev/dashboard
→ Check you have E2B credits

### "Query error"
→ Verify PostHog API key has query permissions
→ Test query in PostHog UI first

### "Tool not executed"
→ Check tool name matches exactly
→ Verify tool is in `tools` parameter

### Still stuck?
→ Check **README.md** troubleshooting section
→ Run tests: `python -m pytest tests/`
→ Check example output in docs

---

## 📦 What You Have

✅ **3 working examples** (minimal, complete, production)
✅ **4 documentation files** (summary, integration, architecture, getting started)
✅ **Core driver** (40 passing tests)
✅ **E2B integration** (sandbox manager + templates)
✅ **Real analysis** (actual PostHog data)
✅ **Production components** (reusable code)

---

## 🎉 Summary

**Your question:** "How could this use Claude Agent SDK?"

**Your answer:**

1. **Minimal:** `minimal_claude_example.py` (100 lines, 3 steps)
2. **Complete:** `claude_agent_with_posthog.py` (350 lines, full agent)
3. **Production:** `agent_executor.py` + templates (reusable components)

**Documentation:**
- **CLAUDE_SDK_SUMMARY.md** ← Main answer
- **ARCHITECTURE_CLAUDE.md** ← Visual diagrams
- **CLAUDE_INTEGRATION.md** ← Deep dive

**Get started:**
```bash
python3 minimal_claude_example.py
```

---

**Questions?** Everything is documented. Use this guide to navigate to what you need.

**Ready to build?** Start with `minimal_claude_example.py` and grow from there.

**Want to understand?** Read `CLAUDE_SDK_SUMMARY.md` first.
