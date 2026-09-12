with open('static/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# The issue is that renderTourismSignals is defined inside loadFmcgSignals
# We need to move renderTourismSignals (and other render functions) to top level
# Let's find the exact boundaries

# Find the loadFmcgSignals function end (should be before loadTourismSignals)
idx_fmcg = content.find('async function loadFmcgSignals')
idx_tourism = content.find('async function loadTourismSignals')
idx_chemical = content.find('async function loadChemicalSignals')
idx_alcohol = content.find('async function loadAlcoholSignals')
idx_lunar1 = content.find('async function loadLunarForecast')
idx_lunar2 = content.rfind('async function loadLunarForecast')
idx_weekly = content.find('async function loadWeeklyCommentary')
idx_bullion = content.find('async function loadBullionVedha')
idx_transit = content.find('async function loadTransitVedha')
idx_run = content.find('async function run')

print('Positions:')
print(f'  loadFmcgSignals: {idx_fmcg}')
print(f'  loadTourismSignals: {idx_tourism}')
print(f'  loadChemicalSignals: {idx_chemical}')
print(f'  loadAlcoholSignals: {idx_alcohol}')
print(f'  loadLunarForecast (1): {idx_lunar1}')
print(f'  loadLunarForecast (2): {idx_lunar2}')
print(f'  loadWeeklyCommentary: {idx_weekly}')
print(f'  loadBullionVedha: {idx_bullion}')
print(f'  loadTransitVedha: {idx_transit}')
print(f'  run: {idx_run}')

# Check for duplicate loadLunarForecast
if idx_lunar1 != idx_lunar2:
    print(f'\nDuplicate loadLunarForecast found at {idx_lunar1} and {idx_lunar2}')
    # Remove the second one
    # Find the end of the second loadLunarForecast
    idx_lunar2_end = content.find('async function loadWeeklyCommentary', idx_lunar2)
    print(f'Second loadLunarForecast ends at: {idx_lunar2_end}')"