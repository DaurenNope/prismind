# 🚫 PRISMIND DEVELOPMENT RULES

## 🎯 CORE PRINCIPLES

### **1. CODEBASE HYGIENE**

-**NO files over 300 lines** - split into smaller, focused modules

-**NO duplicate implementations** - choose ONE and remove the rest

-**NO temporary files** - everything must have a clear purpose

-**NO files without approval** - discuss with user before creating new files

-**NO broken imports** - all imports must work or be properly handled

### **2. FILE ORGANIZATION**

-**Root directory**: Only essential files (main.py, README.md, requirements.txt, config files)

-**src/**: All source code organized by function

-**tests/**: All test files in dedicated directory

-**docs/**: All documentation in dedicated directory

-**logs/**: All log files in dedicated directory

-**config/**: All configuration files in dedicated directory

### **3. DEVELOPMENT WORKFLOW**

-**One component at a time** - never work on multiple components simultaneously

-**Test before proceeding** - every change must be tested immediately

-**Document everything** - every function, class, and module needs documentation

-**Error handling required** - no function without proper error handling

-**Logging required** - all operations must be logged

### **4. INTEGRATION RULES**

-**UI accessible** - all features must work via Streamlit interface

-**Bot accessible** - all features must work via Telegram bot

-**API accessible** - all features must work via REST API

-**Configuration driven** - all settings via environment variables or config files

-**Graceful failures** - system must handle errors without crashing

### **5. TESTING REQUIREMENTS**

-**Triple-check everything** - no assumptions about functionality

-**Test real scenarios** - not just import tests

-**Test error cases** - edge cases and failure modes

-**Test integration** - components working together

-**Document test results** - proof of functionality

### **6. CODE QUALITY**

-**Type hints required** - all functions must have proper type annotations

-**Docstrings required** - all functions must have comprehensive docstrings

-**Consistent naming** - follow Python naming conventions

-**No magic numbers** - all constants must be defined

-**No hardcoded paths** - use configuration for all paths

### **7. PERFORMANCE RULES**

-**Efficient algorithms** - choose appropriate data structures and algorithms

-**Memory management** - avoid memory leaks and excessive memory usage

-**Rate limiting** - respect API rate limits and implement proper delays

-**Caching** - implement caching for expensive operations

-**Monitoring** - track performance metrics

### **8. SECURITY RULES**

-**No credentials in code** - all credentials via environment variables

-**Input validation** - validate all user inputs

-**Error messages** - don't expose sensitive information in error messages

-**Access control** - implement proper authentication and authorization

-**Data protection** - handle sensitive data appropriately

### **9. COMMUNICATION RULES**

-**Ask before creating** - discuss new files/features with user

-**Report progress** - update user on completion of each task

-**Explain decisions** - justify architectural and implementation choices

-**Document changes** - maintain changelog of all modifications

-**Share knowledge** - document learnings and solutions

### **10. MAINTENANCE RULES**

-**Regular cleanup** - remove unused code and files

-**Update dependencies** - keep dependencies current

-**Monitor logs** - review logs for issues and improvements

-**Performance tuning** - optimize based on usage patterns

-**User feedback** - incorporate user feedback into improvements

---

## 🚫 ABSOLUTE PROHIBITIONS

### **NEVER DO THESE:**

1.**Create files without permission** - always ask first

2.**Leave broken code** - fix immediately or remove

3.**Ignore error handling** - every function needs error handling

4.**Skip testing** - every change must be tested

5.**Create duplicates** - choose one implementation and remove others

6.**Write files over 300 lines** - split into smaller modules

7.**Hardcode credentials** - use environment variables

8.**Ignore user feedback** - incorporate user input

9.**Work on multiple components** - focus on one at a time

10.**Assume functionality works** - test everything

### **ALWAYS DO THESE:**

1.**Ask permission** before creating new files

2.**Test immediately** after making changes

3.**Document everything** you do

4.**Handle errors gracefully** in all functions

5.**Follow the plan** religiously

6.**Report progress** to the user

7.**Clean up** after yourself

8.**Validate inputs** in all functions

9.**Log operations** for debugging

10.**Think before coding** - plan the implementation

---

## 📋 CHECKLIST FOR EVERY CHANGE

Before making ANY change, verify:

- [ ] **User approved** this change
- [ ] **File size** under 300 lines
- [ ] **No duplicates** of existing functionality
- [ ] **Error handling** implemented
- [ ] **Logging** added
- [ ] **Documentation** updated
- [ ] **Tests** written and passing
- [ ] **Integration** tested
- [ ] **Configuration** externalized
- [ ] **User notified** of completion

---

## 🎯 SUCCESS CRITERIA

A change is successful when:

1.**Functionality works** - tested and verified

2.**Code is clean** - follows all rules

3.**Documentation updated** - changes documented

4.**User approved** - user confirms satisfaction

5.**Integration tested** - works with other components

6.**Error handling** - graceful failure modes

7.**Performance acceptable** - no performance regression

8.**Maintainable** - easy to understand and modify

9.**Secure** - no security vulnerabilities

10.**Configurable** - settings externalized

---

## 📞 ESCALATION RULES

**Stop and ask user when:**

- Creating new files or modules
- Making architectural changes
- Encountering unexpected errors
- Unsure about implementation approach
- Need to deviate from the plan
- Performance issues arise
- Security concerns identified
- Integration problems occur
- User feedback contradicts plan
- Any uncertainty about next steps

**Remember: Better to ask than assume!**
