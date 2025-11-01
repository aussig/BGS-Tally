# BGS-Tally Improvements

## Changes Summary

This update includes two improvements:
1. **Auto-Sync RavenColonial** - Automatically enable RCSync when assigned to a project
2. **UI Worker Fix** - Prevent startup AttributeError when no system is loaded

---

## 1. Auto-Sync RavenColonial Feature

### Overview
This change automatically creates/tracks systems and enables RavenColonial sync (`RCSync`) when a commander docks at a construction ship or receives colonization data, **if**:
1. A project exists on RavenColonial for that system/market
2. The current commander is assigned to that project

**Key Improvement**: Systems are now **automatically added to BGS-Tally tracking** when you dock at a construction ship where you're assigned to a RavenColonial project - no manual system creation required!

### Changes Made

#### A. `bgstally/ravencolonial.py`
Added new method `check_auto_sync(system_address, market_id)`:
- Checks if a project exists via `/api/system/{systemAddress}/{marketId}`
- Verifies commander assignment via `/api/cmdr/{cmdr}`
- Handles both string buildIds and project objects from API
- Returns `True` if both conditions are met

**Location**: Lines 179-238

#### B. `bgstally/colonisation.py`
Added auto-sync checks in three locations:

**1. ColonisationConstructionDepot Event (Lines 181-199)**
- **Auto-creates system** if it doesn't exist and RavenColonial project + assignment confirmed
- Enables RCSync for existing systems when conditions are met
- Prevents "Invalid ColonisationConstructionDepot event (no system)" warnings

**2. Docked Event - New System Creation (Lines 216-222)**  
- Auto-enables RCSync when creating a new system during construction ship dock
- Checks project assignment before enabling sync

**3. Docked Event - Existing Systems (Lines 234-238)**
- Enables RCSync for already-tracked systems if not yet enabled

## API Endpoints Used

1. **Check Project**: `GET /api/system/{systemAddress}/{marketId}`
   - Returns project data if it exists
   - Returns 404 if no project found

2. **Check Commander Projects**: `GET /api/cmdr/{cmdr}`
   - Returns list of projects the commander is assigned to

## Testing Steps

### Prerequisites
1. Have RavenColonial API key configured in BGS-Tally settings
2. Be assigned to a project on RavenColonial.com

### Test Case 1: Auto-create System (New System)
1. **Remove the system from BGS-Tally** if it exists (or use a fresh colonization system)
2. Dock at a construction ship where you're assigned to a RavenColonial project
3. **Expected**: System automatically added to BGS-Tally with RCSync enabled
4. **Expected Logs**: 
   - "Auto-creating system [system] with RCSync enabled"
   - "Commander [cmdr] is assigned to project [buildId], enabling auto-sync"
5. **Verify**: System appears in BGS-Tally Colonisation window with sync icon (🔄 button visible)

### Test Case 2: Auto-enable for Existing System
1. Have a system already tracked in BGS-Tally with RCSync **disabled**
2. Dock at the construction ship or receive depot data
3. **Expected**: RCSync automatically enables
4. **Expected Log**: "Auto-enabling RCSync for [system]"
5. **Verify**: Contributions now sync to RavenColonial

### Test Case 3: No Auto-create (Not Assigned)
1. Dock at a construction ship where you're **NOT** assigned to the project
2. **Expected**: System is NOT created, warning logged
3. **Expected Log**: "Commander [name] is not assigned to project [id]"
4. **Expected**: "Invalid ColonisationConstructionDepot event (no system)" warning (normal behavior)

### Test Case 4: No Auto-create (No Project)
1. Dock at a construction ship with **no RavenColonial project**
2. **Expected**: System is NOT created
3. **Expected Logs**:
   - "No project found for system [id], market [id]"
   - "Invalid ColonisationConstructionDepot event (no system)" warning (normal behavior)

## Debug Logging

Watch for these log messages:

**Success Messages:**
- `"Auto-creating system {system} with RCSync enabled"` - New system auto-created
- `"Auto-enabling RCSync for newly created system {system}"` - RCSync enabled on dock
- `"Auto-enabling RCSync for {system}"` - RCSync enabled for existing system
- `"Commander {cmdr} is assigned to project {buildId}, enabling auto-sync"` - Assignment confirmed

**Info/Warning Messages:**
- `"No commander set, cannot check auto-sync"` - Commander name not loaded yet
- `"No project found for system {systemAddress}, market {marketId}"` - No RC project exists
- `"Commander {cmdr} is not assigned to project {buildId}"` - Not assigned to this project
- `"Error checking project: {status_code}"` - API error when checking project
- `"Error in check_auto_sync: {error}"` - Exception during auto-sync check

## Potential Issues

1. **API Key Required**: If no API key is configured, requests may fail
2. **Network Timeouts**: 5-second timeout on API calls may be too short in some cases
3. **Duplicate Checks**: Both dock and depot events may trigger - this is intentional for coverage
4. **Rate Limiting**: Multiple API calls per dock event - consider caching if this becomes an issue

---

## 2. UI Worker Startup Fix

### Overview
Fixed an AttributeError that occurred during EDMC startup when the UI worker tried to access system data before it was loaded.

### Changes Made

#### `bgstally/ui.py` (Line 491-493)
Added null check for `current_system` before accessing its attributes:
```python
# Fix: Check if current_system is not None before accessing its attributes
# This prevents AttributeError during startup when no system is loaded yet
if current_system is not None:
    system_tick: str = current_system.get('TickTime')
```

### Error Fixed
```
AttributeError: 'NoneType' object has no attribute 'get'
at ui.py line 490: system_tick: str = current_system.get('TickTime')
```

**Impact**: Prevents harmless but annoying error message during EDMC startup.

---

## Future Improvements

1. Cache project/commander assignment to reduce API calls
2. Add UI notification when auto-sync is enabled
3. Allow users to opt-out of auto-sync via settings
4. Consider async API calls to avoid blocking
