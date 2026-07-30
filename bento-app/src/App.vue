<script>
import { ref, computed, watch, onMounted } from 'vue'
import { auth, db } from './firebase'
import { onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'firebase/auth'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import SearchableSelect from './components/SearchableSelect.vue'

export default {
  components: {
    SearchableSelect
  },
  setup() {
                const user = ref(null);
                const authMode = ref('login');
                const authEmail = ref('');
                const authPassword = ref('');
                const authError = ref('');

                const currentTab = ref('guide');
                
                const ingredients = ref([]);
                const recipes = ref([]);
                const menus = ref([]);
                const showAddIngredientForm = ref(false);
                const showActualsModal = ref(false);
                                const showAddRecipeForm = ref(false);
                const showAddMenuForm = ref(false);

                const sortOrder = ref('added');
                
                const sortedIngredients = computed(() => {
                    if (sortOrder.value === 'added') return ingredients.value;
                    return [...ingredients.value].sort((a, b) => ((a.yomi || a.name) || '').localeCompare((b.yomi || b.name) || '', 'ja'));
                });
                const sortedRecipes = computed(() => {
                    if (sortOrder.value === 'added') return recipes.value;
                    return [...recipes.value].sort((a, b) => ((a.yomi || a.name) || '').localeCompare((b.yomi || b.name) || '', 'ja'));
                });
                const sortedMenus = computed(() => {
                    if (sortOrder.value === 'added') return menus.value;
                    return [...menus.value].sort((a, b) => ((a.yomi || a.name) || '').localeCompare((b.yomi || b.name) || '', 'ja'));
                });

                
                const selectedCalcItems = ref([{ id: Date.now(), menuId: '', peopleCount: 1 }]);

                const addCalcItem = () => {
                    selectedCalcItems.value.push({ id: Date.now(), menuId: '', peopleCount: 1 });
                };

                const removeCalcItem = (index) => {
                    selectedCalcItems.value.splice(index, 1);
                };

                const getMenuById = (id) => menus.value.find(m => m.id === id);

                const hasAnyMemos = computed(() => {
                    return selectedCalcItems.value.some(c => c.menuId && getMenuById(c.menuId)?.memo);
                });

                const calculationResults = computed(() => {
                    const requiredMap = new Map();
                    
                    selectedCalcItems.value.forEach(calcItem => {
                        if (!calcItem.menuId) return;
                        const menu = getMenuById(calcItem.menuId);
                        if (!menu) return;
                        
                        menu.items.forEach(menuItem => {
                            const recipe = recipes.value.find(r => r.id === menuItem.recipeId);
                            if (!recipe) return;
                            
                            recipe.items.forEach(recipeItem => {
                                const ingId = recipeItem.ingredientId;
                                const amountPerPerson = (recipeItem.amount / (recipe.servings || 1)) * menuItem.amount;
                                const totalAmount = amountPerPerson * calcItem.peopleCount;
                                
                                if (requiredMap.has(ingId)) {
                                    const entry = requiredMap.get(ingId);
                                    entry.total += totalAmount;
                                    entry.breakdown[calcItem.id] = (entry.breakdown[calcItem.id] || 0) + totalAmount;
                                } else {
                                    requiredMap.set(ingId, {
                                        total: totalAmount,
                                        breakdown: { [calcItem.id]: totalAmount }
                                    });
                                }
                            });
                        });
                    });
                    
                    const results = [];
                    for (const [ingId, data] of requiredMap.entries()) {
                        const ing = ingredients.value.find(i => i.id === ingId);
                        if (!ing) continue;
                        
                        const missing = Math.max(0, data.total - ing.stock);
                        
                        let buyPkg = 0;
                        if (ing.hasPackage && ing.pkgAmount > 0) {
                            buyPkg = Math.ceil(missing / ing.pkgAmount);
                        }
                        
                        results.push({
                            ...ing,
                            required: data.total,
                            breakdown: data.breakdown,
                            missing,
                            buyPkg
                        });
                    }
                    return results;
                });

                const shoppingList = computed(() => calculationResults.value.filter(i => i.missing > 0));
                const sufficientList = computed(() => calculationResults.value.filter(i => i.missing === 0));

                const formatAmount = (amount, unit, gPerUnit, raw = false) => {
                    if (raw) return parseFloat(amount.toFixed(1));
                    const numStr = Number.isInteger(amount) ? amount : (Math.round(amount * 100) / 100);
                    if (unit === 'g' || unit === 'ml' || gPerUnit === 1 || !gPerUnit || gPerUnit === 0) {
                        return `${numStr} ${unit}`;
                    }
                    const g = Math.round(amount * gPerUnit);
                    return `${numStr} ${unit} (約 ${g}g)`;
                };

                const consumeStock = () => {
                    if (calculationResults.value.length === 0) return;
                    if (!confirm('在庫から必要な量をマイナスしてよろしいですか？')) return;

                    calculationResults.value.forEach(item => {
                        const ing = ingredients.value.find(i => i.id === item.id);
                        if (ing) {
                            ing.stock = Math.max(0, ing.stock - item.required);
                        }
                    });
                    
                    alert('必要な量を在庫からマイナスしました！');
                };

                // 在庫管理ロジック
                let kanaBuffer = '';
                const onCompositionUpdate = (e) => {
                    const text = e.data || '';
                    if (!/[\u4E00-\u9FFF]/.test(text)) {
                        kanaBuffer = text;
                    }
                };
                const onCompositionEnd = (e, targetObj) => {
                    if (kanaBuffer) {
                        let hira = kanaBuffer.replace(/[\u30a1-\u30f6]/g, match =>
                            String.fromCharCode(match.charCodeAt(0) - 0x60)
                        );
                        targetObj.yomi = (targetObj.yomi || '') + hira;
                        kanaBuffer = '';
                    }
                };
                const onInputName = (e, targetObj) => {
                    if (!e.target.value) {
                        targetObj.yomi = '';
                    } else if (!e.isComposing && e.data && !/[\u4E00-\u9FFF]/.test(e.data) && e.inputType === 'insertText') {
                        targetObj.yomi = (targetObj.yomi || '') + e.data;
                    }
                };

                const editingIngredientId = ref(null);
                const newIngredient = ref({ name: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 });
                
                watch(() => newIngredient.value.unit, (newVal) => {
                    newIngredient.value.pkgAmountUnit = newVal;
                });

                const addIngredient = () => {
                    if (!newIngredient.value.name) return;
                    let finalGPerUnit = (newIngredient.value.unit === 'g' || newIngredient.value.unit === 'ml') ? 1 : newIngredient.value.gPerUnit;
                    let finalPkgAmount = newIngredient.value.pkgAmount;
                    if (newIngredient.value.hasPackage && newIngredient.value.pkgAmountUnit === 'g' && newIngredient.value.unit !== 'g' && finalGPerUnit > 0) {
                        finalPkgAmount = newIngredient.value.pkgAmount / finalGPerUnit;
                    }
                    let finalStock = newIngredient.value.displayStock;
                    if (newIngredient.value.hasPackage) {
                        finalStock = newIngredient.value.displayStock * finalPkgAmount;
                    }
                    ingredients.value.push({
                        id: Date.now(),
                        name: newIngredient.value.name,
                        yomi: newIngredient.value.yomi,
                        unit: newIngredient.value.unit,
                        gPerUnit: finalGPerUnit,
                        hasPackage: newIngredient.value.hasPackage,
                        pkgUnit: newIngredient.value.pkgUnit,
                        pkgAmount: finalPkgAmount,
                        stock: finalStock
                    });
                    newIngredient.value = { name: '', yomi: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 };
                    showAddIngredientForm.value = false;
                };
                
                const editIngredient = (ing) => {
                    editingIngredientId.value = ing.id;
                    newIngredient.value = { 
                        ...ing, 
                        pkgAmountUnit: ing.pkgAmountUnit || ing.unit,
                        displayStock: ing.hasPackage ? (ing.stock / ing.pkgAmount) : ing.stock
                    };
                    if (newIngredient.value.yomi === undefined) newIngredient.value.yomi = '';
                    // スクロールして一番上に移動
                    showAddIngredientForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const openAddIngredientForm = () => {
                    editingIngredientId.value = null;
                    newIngredient.value = { name: '', yomi: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 };
                    showAddIngredientForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const cancelEditIngredient = () => {
                    editingIngredientId.value = null;
                    newIngredient.value = { name: '', yomi: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 };
                    showAddIngredientForm.value = false;
                };

                const updateIngredient = () => {
                    if (!newIngredient.value.name || !editingIngredientId.value) return;
                    
                    let finalGPerUnit = (newIngredient.value.unit === 'g' || newIngredient.value.unit === 'ml') ? 1 : newIngredient.value.gPerUnit;
                    let finalPkgAmount = newIngredient.value.pkgAmount;
                    if (newIngredient.value.hasPackage && newIngredient.value.pkgAmountUnit === 'g' && newIngredient.value.unit !== 'g' && finalGPerUnit > 0) {
                        finalPkgAmount = newIngredient.value.pkgAmount / finalGPerUnit;
                    }
                    let finalStock = newIngredient.value.displayStock;
                    if (newIngredient.value.hasPackage) {
                        finalStock = newIngredient.value.displayStock * finalPkgAmount;
                    }
                    
                    const index = ingredients.value.findIndex(i => i.id === editingIngredientId.value);
                    if (index !== -1) {
                        ingredients.value[index] = {
                            id: editingIngredientId.value,
                            name: newIngredient.value.name,
                            yomi: newIngredient.value.yomi,
                            unit: newIngredient.value.unit,
                            gPerUnit: finalGPerUnit,
                            hasPackage: newIngredient.value.hasPackage,
                            pkgUnit: newIngredient.value.pkgUnit,
                            pkgAmount: finalPkgAmount,
                            stock: finalStock
                        };
                    }
                    cancelEditIngredient();
                };

                const removeIngredient = (id) => {
                    ingredients.value = ingredients.value.filter(i => i.id !== id);
                    recipes.value.forEach(r => {
                        r.items = r.items.filter(item => item.ingredientId !== id);
                    });
                };

                // レシピ管理ロジック
                const editingRecipeId = ref(null);
                const newRecipe = ref({ name: '', yomi: '', memo: '', servings: 1, items: [] });
                const newRecipeItem = ref({ ingredientId: '', amount: 1, inputUnit: 'base' });
                watch(() => newRecipeItem.value.ingredientId, () => { newRecipeItem.value.inputUnit = 'base'; });
                
                const printCalculation = () => {
                    window.print();
                };

                const getIngById = (id) => ingredients.value.find(i => i.id === id);
                const getIngName = (id) => {
                    const ing = getIngById(id);
                    return ing ? ing.name : '不明';
                };

                const addIngredientToNewRecipe = () => {
                    if (!newRecipeItem.value.ingredientId) return;
                    let finalAmount = newRecipeItem.value.amount;
                    const ing = getIngById(newRecipeItem.value.ingredientId);
                    if (newRecipeItem.value.inputUnit === 'g' && ing && ing.gPerUnit > 0 && ing.unit !== 'g') {
                        finalAmount = newRecipeItem.value.amount / ing.gPerUnit;
                    }
                    newRecipe.value.items.push({
                        ingredientId: newRecipeItem.value.ingredientId,
                        amount: finalAmount
                    });
                    newRecipeItem.value = { ingredientId: '', amount: 1, inputUnit: 'base' };
                };
                const removeIngredientFromNewRecipe = (idx) => {
                    newRecipe.value.items.splice(idx, 1);
                };
                const addNewRecipe = () => {
                    if (!newRecipe.value.name || newRecipe.value.items.length === 0) return;
                    recipes.value.push({
                        id: Date.now(),
                        name: newRecipe.value.name,
                        yomi: newRecipe.value.yomi,
                        memo: newRecipe.value.memo,
                        servings: newRecipe.value.servings || 1,
                        items: [...newRecipe.value.items]
                    });
                    newRecipe.value = { name: '', yomi: '', memo: '', servings: 1, items: [] };
                };
                
                const editRecipe = (recipe) => {
                    editingRecipeId.value = recipe.id;
                    newRecipe.value = { 
                        name: recipe.name,
                        yomi: recipe.yomi || '',
                        memo: recipe.memo,
                        servings: recipe.servings || 1,
                        items: JSON.parse(JSON.stringify(recipe.items))
                    };
                    showAddRecipeForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const openAddRecipeForm = () => {
                    editingRecipeId.value = null;
                    newRecipe.value = { name: '', yomi: '', memo: '', servings: 1, items: [] };
                    showAddRecipeForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const cancelEditRecipe = () => {
                    editingRecipeId.value = null;
                    newRecipe.value = { name: '', yomi: '', memo: '', servings: 1, items: [] };
                    showAddRecipeForm.value = false;
                };

                const updateRecipe = () => {
                    if (!newRecipe.value.name || newRecipe.value.items.length === 0 || !editingRecipeId.value) return;
                    const index = recipes.value.findIndex(r => r.id === editingRecipeId.value);
                    if (index !== -1) {
                        recipes.value[index] = {
                            id: editingRecipeId.value,
                            name: newRecipe.value.name,
                            yomi: newRecipe.value.yomi,
                            memo: newRecipe.value.memo,
                            servings: newRecipe.value.servings || 1,
                            items: [...newRecipe.value.items]
                        };
                    }
                    cancelEditRecipe();
                };

                const removeRecipe = (id) => {
                    recipes.value = recipes.value.filter(r => r.id !== id);
                    menus.value.forEach(m => {
                        m.items = m.items.filter(item => item.recipeId !== id);
                    });
                };
                // メニュー管理ロジック
                const editingMenuId = ref(null);
                const newMenu = ref({ name: '', yomi: '', memo: '', items: [] });
                const newMenuItem = ref({ recipeId: '', amount: 1 });
                
                const dragMenuIndex = ref(null);
                const onMenuDragStart = (event, index) => {
                    dragMenuIndex.value = index;
                    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
                };
                const onMenuDrop = (event, dropIndex) => {
                    const dragIndex = dragMenuIndex.value;
                    if (dragIndex !== null && dragIndex !== dropIndex) {
                        const items = newMenu.value.items;
                        const [draggedItem] = items.splice(dragIndex, 1);
                        items.splice(dropIndex, 0, draggedItem);
                    }
                    dragMenuIndex.value = null;
                };

                const addRecipeToNewMenu = () => {
                    if (!newMenuItem.value.recipeId) return;
                    newMenu.value.items.push({...newMenuItem.value});
                    newMenuItem.value = { recipeId: '', amount: 1 };
                };

                const removeRecipeFromNewMenu = (idx) => {
                    newMenu.value.items.splice(idx, 1);
                };

                const getRecipeById = (id) => recipes.value.find(r => r.id === id);
                const getRecipeName = (id) => {
                    const r = getRecipeById(id);
                    return r ? r.name : '不明';
                };
                const addNewMenu = () => {
                    const validItems = newMenu.value.items.filter(i => i.recipeId);
                    if (!newMenu.value.name || validItems.length === 0) return;
                    menus.value.push({
                        id: Date.now(),
                        name: newMenu.value.name,
                        yomi: newMenu.value.yomi,
                        memo: newMenu.value.memo,
                        items: validItems.map(i => ({ recipeId: i.recipeId, amount: i.amount }))
                    });
                    newMenu.value = { name: '', yomi: '', memo: '', items: [] };
                    showAddMenuForm.value = false;
                };

                const editMenu = (menu) => {
                    editingMenuId.value = menu.id;
                    newMenu.value = { 
                        name: menu.name,
                        yomi: menu.yomi || '',
                        memo: menu.memo,
                        items: JSON.parse(JSON.stringify(menu.items))
                    };
                    showAddMenuForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const openAddMenuForm = () => {
                    editingMenuId.value = null;
                    newMenu.value = { name: '', yomi: '', memo: '', items: [] };
                    showAddMenuForm.value = true;
                    setTimeout(() => {
                        const mainContent = document.querySelector('.main-content');
                        if (mainContent) mainContent.scrollTo({ top: mainContent.scrollHeight, behavior: 'smooth' });
                    }, 50);
                };

                const cancelEditMenu = () => {
                    editingMenuId.value = null;
                    newMenu.value = { name: '', yomi: '', memo: '', items: [] };
                    showAddMenuForm.value = false;
                };

                const updateMenu = () => {
                    const validItems = newMenu.value.items.filter(i => i.recipeId);
                    if (!newMenu.value.name || validItems.length === 0 || !editingMenuId.value) return;
                    
                    const idx = menus.value.findIndex(m => m.id === editingMenuId.value);
                    if (idx !== -1) {
                        menus.value[idx] = {
                            ...menus.value[idx],
                            name: newMenu.value.name,
                            yomi: newMenu.value.yomi,
                            memo: newMenu.value.memo,
                            items: validItems.map(i => ({ recipeId: i.recipeId, amount: i.amount }))
                        };
                    }
                    cancelEditMenu();
                };

                const removeMenu = (id) => {
                    menus.value = menus.value.filter(m => m.id !== id);
                };

                // 週間仕入れロジック

                const weeklyPlan = ref([{ id: Date.now(), menuId: '', peopleCount: 30 }]);
                const dailyPlanToday = ref([]);
                const dailyPlanTomorrow = ref([]);
                const dailyActuals = ref({});
                const bentoDestinations = ref({
                    date: '', no1: '', no2: '', no3: '', no4: '', no5: '', no6: '', honsha: '',
                    e: '', w: '', familia: '', hajime: '', kishigawa: ''
                });

                
                const addWeeklyPlanItem = () => {
                    weeklyPlan.value.push({ id: Date.now(), menuId: '', peopleCount: 30 });
                };
                const removeWeeklyPlanItem = (idx) => {
                    weeklyPlan.value.splice(idx, 1);
                };
                
                const bentoSubtotal1 = computed(() => Number(bentoDestinations.value.no1||0) + Number(bentoDestinations.value.no2||0) + Number(bentoDestinations.value.no3||0) + Number(bentoDestinations.value.no4||0) + Number(bentoDestinations.value.no5||0) + Number(bentoDestinations.value.no6||0) + Number(bentoDestinations.value.honsha||0));
                const bentoSubtotal2 = computed(() => Number(bentoDestinations.value.e||0) + Number(bentoDestinations.value.w||0));
                const bentoSubtotal3 = computed(() => Number(bentoDestinations.value.familia||0) + Number(bentoDestinations.value.hajime||0) + Number(bentoDestinations.value.kishigawa||0));
                const bentoGrandTotal = computed(() => bentoSubtotal1.value + bentoSubtotal2.value + bentoSubtotal3.value);

                const calendarYear = ref(new Date().getFullYear());
                const calendarMonth = ref(new Date().getMonth());
                const calendarData = ref({});

                const calendarWeeks = computed(() => {
                    const year = calendarYear.value;
                    const month = calendarMonth.value;
                    const weeks = [];
                    const firstDay = new Date(year, month, 1);
                    const lastDay = new Date(year, month + 1, 0);
                    
                    let currentDate = new Date(firstDay);
                    let diff = currentDate.getDay() - 1;
                    if (diff < 0) diff = 6;
                    currentDate.setDate(currentDate.getDate() - diff);
                    
                    while (currentDate <= lastDay || currentDate.getDay() !== 1) {
                        let week = [];
                        for (let i = 0; i < 7; i++) {
                            week.push({
                                date: new Date(currentDate),
                                dateNum: currentDate.getDate(),
                                isCurrentMonth: currentDate.getMonth() === month,
                                dayIndex: currentDate.getDay()
                            });
                            currentDate.setDate(currentDate.getDate() + 1);
                        }
                        const workDays = week.filter(d => d.dayIndex >= 1 && d.dayIndex <= 5);
                        if (workDays.some(d => d.isCurrentMonth)) {
                            weeks.push(workDays);
                        }
                        if (currentDate > lastDay && currentDate.getDay() === 1) break;
                    }
                    return weeks;
                });

                const prevCalendarMonth = () => {
                    if (calendarMonth.value === 0) {
                        calendarMonth.value = 11;
                        calendarYear.value--;
                    } else {
                        calendarMonth.value--;
                    }
                };

                const nextCalendarMonth = () => {
                    if (calendarMonth.value === 11) {
                        calendarMonth.value = 0;
                        calendarYear.value++;
                    } else {
                        calendarMonth.value++;
                    }
                };


                const addDailyPlanTodayItem = () => { dailyPlanToday.value.push({ id: Date.now(), menuId: '', peopleCount: 30 }); };
                const removeDailyPlanTodayItem = (idx) => { dailyPlanToday.value.splice(idx, 1); };
                
                const addDailyPlanTomorrowItem = () => { dailyPlanTomorrow.value.push({ id: Date.now(), recipeId: '', peopleCount: 30 }); };
                const removeDailyPlanTomorrowItem = (idx) => { dailyPlanTomorrow.value.splice(idx, 1); };

                const todayExpectedIngredients = computed(() => {
                    const req = {};
                    dailyPlanToday.value.forEach(plan => {
                        if (!plan.menuId || !plan.peopleCount) return;
                        const menu = menus.value.find(m => m.id === plan.menuId);
                        if (!menu) return;
                        menu.items.forEach(menuItem => {
                            const recipe = recipes.value.find(r => r.id === menuItem.recipeId);
                            if (!recipe) return;
                            recipe.items.forEach(recipeItem => {
                                const totalIngAmount = (recipeItem.amount / (recipe.servings || 1)) * menuItem.amount * plan.peopleCount;
                                req[recipeItem.ingredientId] = (req[recipeItem.ingredientId] || 0) + totalIngAmount;
                            });
                        });
                    });
                    
                    const list = [];
                    Object.keys(req).forEach(ingIdStr => {
                        const ingId = parseInt(ingIdStr);
                        const ing = ingredients.value.find(i => i.id === ingId);
                        if (!ing) return;
                        list.push({ ...ing, required: req[ingId] });
                    });
                    return list.sort((a, b) => ((a.yomi || a.name) || '').localeCompare((b.yomi || b.name) || '', 'ja'));
                });
                const todayExpectedIngredientsByMenu = computed(() => {
                    const menuGroups = [];
                    dailyPlanToday.value.forEach(plan => {
                        if (!plan.menuId || !plan.peopleCount) return;
                        const menu = menus.value.find(m => m.id === plan.menuId);
                        if (!menu) return;
                        
                        const recipesInMenu = [];
                        menu.items.forEach(menuItem => {
                            const recipe = recipes.value.find(r => r.id === menuItem.recipeId);
                            if (!recipe) return;
                            
                            const reqList = [];
                            recipe.items.forEach(recipeItem => {
                                const totalIngAmount = (recipeItem.amount / (recipe.servings || 1)) * menuItem.amount * plan.peopleCount;
                                const ing = ingredients.value.find(i => i.id === recipeItem.ingredientId);
                                if (ing) {
                                    // if already exists in reqList, add to it
                                    const existing = reqList.find(x => x.id === ing.id);
                                    if (existing) {
                                        existing.required += totalIngAmount;
                                    } else {
                                        reqList.push({ ...ing, required: totalIngAmount });
                                    }
                                }
                            });
                            
                            recipesInMenu.push({
                                recipe: recipe,
                                amount: menuItem.amount,
                                ingredients: reqList
                            });
                        });
                        
                        menuGroups.push({
                            id: plan.id,
                            menu: menu,
                            portions: plan.peopleCount,
                            recipes: recipesInMenu
                        });
                    });
                    return menuGroups;
                });


                const tomorrowPrepRecipes = computed(() => {
                    const recipeGroup = {};
                    dailyPlanTomorrow.value.forEach(plan => {
                        if (!plan.recipeId || !plan.peopleCount) return;
                        const recipe = recipes.value.find(r => r.id === plan.recipeId);
                        if (!recipe) return;
                        
                        const totalPortions = plan.peopleCount;
                        if (!recipeGroup[recipe.id]) {
                            recipeGroup[recipe.id] = { recipe: recipe, portions: 0, ingredientsReq: {} };
                        }
                        recipeGroup[recipe.id].portions += totalPortions;
                        
                        recipe.items.forEach(recipeItem => {
                            const totalIngAmount = (recipeItem.amount / (recipe.servings || 1)) * totalPortions;
                            recipeGroup[recipe.id].ingredientsReq[recipeItem.ingredientId] = 
                                (recipeGroup[recipe.id].ingredientsReq[recipeItem.ingredientId] || 0) + totalIngAmount;
                        });
                    });
                    return Object.values(recipeGroup).sort((a, b) => ((a.recipe.yomi || a.recipe.name) || '').localeCompare((b.recipe.yomi || b.recipe.name) || '', 'ja'));
                });

                const deductStock = () => {
                    if (!confirm("入力された実績で在庫を減らしますか？")) return;
                    todayExpectedIngredients.value.forEach(item => {
                        const usedAmount = dailyActuals.value[item.id] !== undefined && dailyActuals.value[item.id] !== '' ? Number(dailyActuals.value[item.id]) : item.required;
                        if (usedAmount > 0) {
                            const ing = ingredients.value.find(i => i.id === item.id);
                            if (ing) ing.stock = Math.max(0, (ing.stock || 0) - usedAmount);
                        }
                    });
                    alert("在庫を引き落としました！");
                    dailyActuals.value = {};
                };

                const weeklyShoppingList = computed(() => {

                    const req = {};
                    
                    // 1. すべての予定を合算
                    weeklyPlan.value.forEach(plan => {
                        if (!plan.menuId || !plan.peopleCount) return;
                        const menu = menus.value.find(m => m.id === plan.menuId);
                        if (!menu) return;
                        
                        menu.items.forEach(menuItem => {
                            const recipe = recipes.value.find(r => r.id === menuItem.recipeId);
                            if (!recipe) return;
                            
                            recipe.items.forEach(recipeItem => {
                                const totalIngAmount = recipeItem.amount * menuItem.amount * plan.peopleCount;
                                req[recipeItem.ingredientId] = (req[recipeItem.ingredientId] || 0) + totalIngAmount;
                            });
                        });
                    });

                    // 2. 在庫と照らし合わせて買うべき量を計算
                    const list = [];
                    Object.keys(req).forEach(ingIdStr => {
                        const ingId = parseInt(ingIdStr);
                        const ing = ingredients.value.find(i => i.id === ingId);
                        if (!ing) return;

                        const totalRequired = req[ingId];
                        const shortage = Math.max(0, totalRequired - ing.stock);
                        
                        let buyPackages = 0;
                        if (shortage > 0 && ing.hasPackage && ing.pkgAmount > 0) {
                            buyPackages = Math.ceil(shortage / ing.pkgAmount);
                        }

                        list.push({
                            ...ing,
                            required: totalRequired,
                            shortage: shortage,
                            buyPackages: buyPackages
                        });
                    });

                    return list.sort((a, b) => b.shortage - a.shortage);
                });

                // データのロードと保存処理
                const loadData = async (uid) => {
                    try {
                        const docRef = doc(db, 'users', uid);
                        const docSnap = await getDoc(docRef);
                        if (docSnap.exists()) {
                            const data = docSnap.data();
                            ingredients.value = data.ingredients || [];
                            recipes.value = data.recipes || [];
                            menus.value = data.menus || [];

                            if (data.weeklyPlan) weeklyPlan.value = data.weeklyPlan;
                            if (data.dailyPlanToday) dailyPlanToday.value = data.dailyPlanToday;
                            if (data.dailyPlanTomorrow) dailyPlanTomorrow.value = data.dailyPlanTomorrow;
                            if (data.dailyActuals) dailyActuals.value = data.dailyActuals;
                            if (data.bentoDestinations) bentoDestinations.value = data.bentoDestinations;
                            if (data.calendarData) calendarData.value = data.calendarData;
                            if (data.calendarYear !== undefined) calendarYear.value = data.calendarYear;
                            if (data.calendarMonth !== undefined) calendarMonth.value = data.calendarMonth;

                            
                            // If they have ingredients, they don't need the guide anymore
                            if (ingredients.value.length > 0 && currentTab.value === 'guide') {
                                currentTab.value = 'inventory';
                            }
                        } else {
                            // Default data
                            ingredients.value = [
                                { id: 1, name: 'にんじん', yomi: 'にんじん', unit: '本', gPerUnit: 150, stock: 0.5 },
                                { id: 2, name: 'じゃがいも', yomi: 'じゃがいも', unit: '個', gPerUnit: 150, stock: 2 }
                            ];
                            recipes.value = [];
                            menus.value = [];
                        }
                    } catch (e) {
                        console.error("Error loading data:", e);
                    }
                };

                const saveData = async () => {
                    if (!user.value) return;
                    try {
                        const plainData = JSON.parse(JSON.stringify({
                            ingredients: ingredients.value,
                            recipes: recipes.value,
                            menus: menus.value,

                            weeklyPlan: weeklyPlan.value,
                            dailyPlanToday: dailyPlanToday.value,
                            dailyPlanTomorrow: dailyPlanTomorrow.value,
                            dailyActuals: dailyActuals.value,
                            bentoDestinations: bentoDestinations.value,
                            calendarData: calendarData.value,
                            calendarYear: calendarYear.value,
                            calendarMonth: calendarMonth.value
                        }));
                        await setDoc(doc(db, 'users', user.value.uid), plainData);
                    } catch (e) {
                        console.error("Error saving data:", e);
                        alert("保存エラーが発生しました: " + e.message);
                    }
                };

                onMounted(() => {
                    onAuthStateChanged(auth, (u) => {
                        if (u) {
                            user.value = u;
                            loadData(u.uid);
                        } else {
                            user.value = null;
                        }
                    });
                });

                watch([ingredients, recipes, menus, weeklyPlan, dailyPlanToday, dailyPlanTomorrow, bentoDestinations, calendarData, calendarYear, calendarMonth], () => {
                    saveData();
                }, { deep: true });

                const handleLogin = async () => {
                    authError.value = '';
                    try {
                        if (authMode.value === 'login') {
                            await signInWithEmailAndPassword(auth, authEmail.value, authPassword.value);
                        } else {
                            await createUserWithEmailAndPassword(auth, authEmail.value, authPassword.value);
                        }
                    } catch(e) {
                        authError.value = '認証エラー: ' + e.message;
                    }
                };

                const handleLogout = async () => {
                    await signOut(auth);
                };

                return {
                    sortedIngredients, sortedRecipes, sortedMenus, sortOrder, showAddIngredientForm, openAddIngredientForm, showAddRecipeForm, openAddRecipeForm, showAddMenuForm, openAddMenuForm,
                    currentTab, ingredients, recipes, menus, selectedCalcItems, addCalcItem, removeCalcItem, getMenuById, hasAnyMemos, 
                    calculationResults, shoppingList, sufficientList, formatAmount, 
                    newIngredient, addIngredient, removeIngredient, editingIngredientId, editIngredient, cancelEditIngredient, updateIngredient,
                    newRecipe, newRecipeItem, addNewRecipe, removeRecipe, addIngredientToNewRecipe, removeIngredientFromNewRecipe, editingRecipeId, editRecipe, cancelEditRecipe, updateRecipe,
                    newMenu, newMenuItem, addNewMenu, removeMenu, addRecipeToNewMenu, removeRecipeFromNewMenu, editingMenuId, editMenu, cancelEditMenu, updateMenu, 
                    onMenuDragStart, onMenuDrop, 
                    onCompositionUpdate, onCompositionEnd, onInputName,
                    user, authMode, authEmail, authPassword, authError, handleLogin, handleLogout,

                    weeklyPlan, addWeeklyPlanItem, removeWeeklyPlanItem, weeklyShoppingList,
                    dailyPlanToday, dailyPlanTomorrow, dailyActuals, addDailyPlanTodayItem, removeDailyPlanTodayItem,
                    addDailyPlanTomorrowItem, removeDailyPlanTomorrowItem, todayExpectedIngredients, todayExpectedIngredientsByMenu, showActualsModal, tomorrowPrepRecipes, deductStock,
                    bentoDestinations, bentoSubtotal1, bentoSubtotal2, bentoSubtotal3, bentoGrandTotal,
                    calendarYear, calendarMonth, calendarWeeks, prevCalendarMonth, nextCalendarMonth, calendarData,

                    getIngById, getIngName, getRecipeById, getRecipeName, consumeStock, printCalculation
                };
            
  }
}
</script>

<template>
  <div class="app-container">
    <div v-if="!user" style="display:flex; align-items:center; justify-content:center; width:100%; height:100vh; background:var(--bg-color);">
        <div class="card" style="width: 100%; max-width: 400px;">
            <h1 style="text-align:center; margin-bottom:2rem;">BentoBox</h1>
            <div class="form-group">
                <label>メールアドレス</label>
                <input type="email" v-model="authEmail" placeholder="you@example.com">
            </div>
            <div class="form-group">
                <label>パスワード (6文字以上)</label>
                <input type="password" v-model="authPassword" placeholder="******">
            </div>
            <div v-if="authError" style="color:var(--danger); margin-bottom:1rem; font-size:0.9rem;">{{ authError }}</div>
            <button class="btn btn-primary" style="width:100%; margin-bottom:1rem;" @click="handleLogin">
                {{ authMode === 'login' ? 'ログイン' : '新規登録' }}
            </button>
            <div style="text-align:center; font-size:0.9rem;">
                <a href="#" @click.prevent="authMode = authMode === 'login' ? 'register' : 'login'" style="color:var(--primary);">
                    {{ authMode === 'login' ? '新規アカウント作成はこちら' : 'ログイン画面に戻る' }}
                </a>
            </div>
        </div>
    </div>
    <template v-else>


        <!-- Sidebar / Navigation -->
        <nav class="sidebar">
            <div class="logo">BentoBox</div>
            <ul class="nav-links">
                <li v-if="ingredients.length === 0" :class="{ active: currentTab === 'guide' }" @click="currentTab = 'guide'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                    <span>はじめに</span>
                </li>
                <li :class="{ active: currentTab === 'inventory' }" @click="currentTab = 'inventory'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                    <span>在庫</span>
                </li>
                <li :class="{ active: currentTab === 'recipes' }" @click="currentTab = 'recipes'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
                    <span>レシピ</span>
                </li>
                <li :class="{ active: currentTab === 'menus' }" @click="currentTab = 'menus'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
                    <span>メニュー</span>
                </li>
                <li :class="{ active: currentTab === 'daily', 'hide-on-mobile': true }" @click="currentTab = 'daily'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    <span>実績</span>
                </li>
                <li :class="{ active: currentTab === 'shopping', 'hide-on-mobile': true }" @click="currentTab = 'shopping'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
                    <span>仕入れ</span>
                </li>
                <li :class="{ active: currentTab === 'calendar', 'hide-on-mobile': true }" @click="currentTab = 'calendar'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                    <span>カレンダー</span>
                </li>
            </ul>
        <button class="btn btn-danger logout-btn" @click="handleLogout">ログアウト</button>
        </nav>


        <!-- Main Content -->
        <main class="main-content">


            
            <!-- TAB: Guide -->
            <div v-if="currentTab === 'guide'" class="tab-pane">
                <header>
                    <h1>はじめての方へ</h1>
                    <p>BentoBoxをご利用いただきありがとうございます！以下のステップでお弁当システムを設定しましょう。</p>
                </header>

                <div class="card" style="margin-bottom: 2rem;">
                    <h2 style="color: var(--primary-dark); margin-bottom: 1rem;">ステップ 1: 材料を登録する</h2>
                    <p>まずは左側のメニューから <strong>「在庫・材料」</strong> を開き、普段お弁当に使う材料（お肉、野菜、調味料など）を登録しましょう。<br>
                    グラム（g）や個数など、管理しやすい単位で登録できます。</p>
                </div>

                <div class="card" style="margin-bottom: 2rem;">
                    <h2 style="color: var(--primary-dark); margin-bottom: 1rem;">ステップ 2: おかずレシピを作る</h2>
                    <p>次に <strong>「おかずレシピ」</strong> を開きます。<br>
                    ステップ1で登録した材料を組み合わせて、「定番の卵焼き」や「唐揚げ」などのレシピ（1人前）を作成します。</p>
                </div>

                <div class="card" style="margin-bottom: 2rem;">
                    <h2 style="color: var(--primary-dark); margin-bottom: 1rem;">ステップ 3: お弁当メニューを組む</h2>
                    <p><strong>「お弁当メニュー」</strong> を開き、作成した「おかずレシピ」を組み合わせて、一つのお弁当メニュー（例：唐揚げ弁当）を完成させましょう。</p>
                </div>

                <div class="card" style="background: var(--primary-light); border-left: 4px solid var(--primary);">
                    <h2 style="color: var(--primary-dark); margin-bottom: 1rem;">準備完了！使い始めましょう</h2>
                    <p>ここまでの設定が終われば準備完了です！<br>
                    <strong>「必要量計算」</strong> や <strong>「週間仕入れ」</strong> タブを開いて、必要な材料を自動計算し、買い物リストとして活用してください！</p>
                </div>
            </div>
            <!-- TAB: Inventory -->
            <div v-if="currentTab === 'inventory'" class="tab-pane">
                <header>
                    <h1>在庫・材料マスター</h1>
                    <p>冷蔵庫にある材料と、それぞれの目安グラムを登録します。</p>
                </header>

                <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
                    <label style="display:flex; align-items:center; gap:0.25rem; font-size:0.9rem; font-weight:600; color:var(--primary); white-space: nowrap; cursor: pointer;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M7 12h10"></path><path d="M10 18h4"></path></svg>
                        並び順:
                        <select v-model="sortOrder" style="padding: 0.2rem; border:none; background:transparent; color: var(--primary); font-weight: 600; cursor: pointer; outline: none; -webkit-appearance: none; appearance: none;">
                            <option value="added">追加した順</option>
                            <option value="alphabetical">あいうえお順</option>
                        </select>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:-4px;"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </label>
                </div>

                <div v-if="!showAddIngredientForm" class="card add-card" style="margin-bottom: 1.5rem; min-height: 60px; flex-direction: row; gap: 0.5rem; padding: 0.5rem;" @click="openAddIngredientForm">
                    <div class="add-card-icon" style="font-size: 2rem; margin-bottom: 0; font-weight: 400;">+</div>
                    <div class="add-card-text" style="font-size: 1rem;">新しい材料を登録</div>
                </div>
                <!-- Ingredient List -->
                <div class="card" style="padding: 0; overflow-x: auto;">
                    <table class="list-table">
                        <thead>
                            <tr>
                                <th>名前</th>
                                <th class="hide-on-mobile">単位</th>
                                <th class="hide-on-mobile">目安グラム換算</th>
                                <th>現在庫</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="ing in sortedIngredients" :key="ing.id">
                                <td style="font-weight: 600;">{{ ing.name }}</td>
                                <td class="hide-on-mobile">{{ ing.unit }}</td>
                                <td class="hide-on-mobile">
                                    <span v-if="ing.unit === 'g' || ing.unit === 'ml'">-</span>
                                    <span v-else-if="!ing.gPerUnit || ing.gPerUnit === 0">換算なし</span>
                                    <span v-else>1{{ ing.unit }} ＝ 約{{ ing.gPerUnit }}g</span>
                                </td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                                        <template v-if="ing.hasPackage">
                                            <input type="number" :value="Math.round((ing.stock / ing.pkgAmount) * 100) / 100" @input="ing.stock = $event.target.value * ing.pkgAmount" min="0" step="1" style="width:80px; padding: 0.4rem;">
                                            {{ ing.pkgUnit }}
                                            <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">
                                                (約 {{ Math.round(ing.stock * 10) / 10 }} {{ ing.unit }})
                                            </span>
                                        </template>
                                        <template v-else>
                                            <input type="number" v-model.number="ing.stock" min="0" step="1" style="width:80px; padding: 0.4rem;">
                                            {{ ing.unit }}
                                        </template>
                                    </div>
                                </td>
                                <td>
                                    <div style="display:flex; gap: 0.5rem;">
                                        <button class="btn" style="padding: 0.25rem 0.5rem; background: var(--surface); color: var(--text);" @click="editIngredient(ing)">編集</button>
                                        <button class="btn btn-danger" style="padding: 0.25rem 0.5rem;" @click="removeIngredient(ing.id)">削除</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-if="!showAddIngredientForm" class="card add-card" style="margin-top: 1.5rem; margin-bottom: 0; min-height: 100px;" @click="openAddIngredientForm">
                    <div class="add-card-icon">+</div>
                    <div class="add-card-text">新しい材料を登録</div>
                </div>
<!-- Add New Ingredient -->
                <div class="card" v-if="showAddIngredientForm">
                    <h3 v-if="!editingIngredientId">新しい材料を登録</h3>
                    <h3 v-else>材料を編集</h3>
                    <div class="flex-row" style="margin-top: 1rem; align-items: flex-start; flex-wrap: wrap;">
                        <div style="display: flex; flex-direction: column; min-width: 200px; flex: 1.5; gap: 0.5rem; margin-right: 1rem;">
                            <div class="form-group" style="margin-bottom: 0;">
                                <label>名前 <span style="color:var(--danger)">*</span></label>
                                <input type="text" v-model="newIngredient.name" placeholder="例: 冷凍唐揚げ"
                                       @compositionupdate="onCompositionUpdate"
                                       @compositionend="onCompositionEnd($event, newIngredient)"
                                       @input="onInputName($event, newIngredient)">
                            </div>
                            <div class="form-group" style="margin-bottom: 0;">
                                <label>ふりがな <span style="font-size:0.8rem; color:var(--muted); font-weight:normal;">(あいうえお順用)</span></label>
                                <input type="text" v-model="newIngredient.yomi" placeholder="例: れいとうからあげ">
                            </div>
                        </div>
                        <div class="form-group" style="width: 80px;">
                            <label>基本単位</label>
                            <select v-model="newIngredient.unit">
                                <option value="個">個</option>
                                <option value="本">本</option>
                                <option value="枚">枚</option>
                                <option value="合">合</option>
                                <option value="g">g</option>
                                <option value="ml">ml</option>
                            </select>
                        </div>
                        <div class="form-group" style="flex: 1; min-width: 200px;" v-if="newIngredient.unit !== 'g' && newIngredient.unit !== 'ml'">
                            <label>1{{ newIngredient.unit }}は何グラムですか？ <span style="font-size: 0.8em; color: var(--text-muted);">(任意)</span></label>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <input type="number" v-model.number="newIngredient.gPerUnit" min="0" placeholder="0">
                                <span>g</span>
                            </div>
                            <div class="hint-text">※レシピで「グラム」指定する時の計算用です。分からない場合は0でOKです。</div>
                        </div>

                        <!-- パック・袋買い設定 -->
                        <div class="form-group" style="background: #f9fafb; padding: 0.5rem 1rem; border-radius: 8px; flex: 1; min-width: 250px;">
                            <label style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                                <input type="checkbox" v-model="newIngredient.hasPackage" style="width: auto;">
                                <span>袋やパックでまとめ買いする</span>
                            </label>
                            <div v-if="newIngredient.hasPackage" style="display:flex; align-items:center; gap:0.5rem;">
                                <span>1</span>
                                <input type="text" v-model="newIngredient.pkgUnit" placeholder="袋" style="width: 60px; padding:0.4rem;">
                                <span>＝</span>
                                <input type="number" v-model.number="newIngredient.pkgAmount" min="1" style="width: 70px; padding:0.4rem;">
                                <select v-model="newIngredient.pkgAmountUnit" style="width: 70px; padding:0.4rem;" v-if="newIngredient.unit !== 'g' && newIngredient.unit !== 'ml' && newIngredient.gPerUnit > 0">
                                    <option :value="newIngredient.unit">{{ newIngredient.unit }}</option>
                                    <option value="g">g</option>
                                </select>
                                <span v-else>{{ newIngredient.unit }}</span>
                            </div>
                            <div v-if="newIngredient.hasPackage && newIngredient.pkgAmountUnit === 'g' && newIngredient.gPerUnit > 0" class="hint-text" style="margin-top: 0.5rem; color: var(--primary-dark);">
                                (1袋 ＝ 約 {{ Math.floor(newIngredient.pkgAmount / newIngredient.gPerUnit) }} {{ newIngredient.unit }} 分として計算します)
                            </div>
                        </div>

                        <div class="form-group">
                            <label>現在庫 ({{ newIngredient.hasPackage ? newIngredient.pkgUnit : newIngredient.unit }})</label>
                            <input type="number" v-model.number="newIngredient.displayStock" min="0" step="0.1" style="width: 100px;">
                        </div>
                        
                        <div class="form-group" style="align-self: flex-end; display: flex; gap: 0.5rem;">
                            <template v-if="!editingIngredientId">
                                <button class="btn btn-primary" @click="addIngredient">追加</button>
                                <button class="btn" style="background: var(--surface); color: var(--text);" @click="cancelEditIngredient">キャンセル</button>
                            </template>
                            <template v-else>
                                <button class="btn btn-primary" @click="updateIngredient">更新</button>
                                <button class="btn" style="background: var(--surface); color: var(--text);" @click="cancelEditIngredient">キャンセル</button>
                            </template>
                        </div>
                    </div>
                </div>

                
            </div>


            <!-- TAB: Recipes -->
            <div v-if="currentTab === 'recipes'" class="tab-pane">
                <header>
                    <h1>おかずレシピ管理</h1>
                    <p>お弁当に入る「おかず（卵焼き等）」と、その1人前に必要な材料を登録します。</p>
                </header>


                <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
                    <label style="display:flex; align-items:center; gap:0.25rem; font-size:0.9rem; font-weight:600; color:var(--primary); white-space: nowrap; cursor: pointer;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M7 12h10"></path><path d="M10 18h4"></path></svg>
                        並び順:
                        <select v-model="sortOrder" style="padding: 0.2rem; border:none; background:transparent; color: var(--primary); font-weight: 600; cursor: pointer; outline: none; -webkit-appearance: none; appearance: none;">
                            <option value="added">追加した順</option>
                            <option value="alphabetical">あいうえお順</option>
                        </select>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:-4px;"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </label>
                </div>
                <!-- Existing Recipes -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
                    <div class="card" v-for="recipe in sortedRecipes" :key="recipe.id" style="margin-bottom: 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                            <h3>{{ recipe.name }}</h3>
                            <div style="display:flex; gap: 0.5rem;">
                                <button class="btn" style="padding: 0.25rem 0.5rem; font-size: 0.85rem; background: var(--surface); color: var(--text);" @click="editRecipe(recipe)">編集</button>
                                <button class="btn btn-danger" style="padding: 0.25rem 0.75rem;" @click="removeRecipe(recipe.id)">削除</button>
                            </div>
                        </div>
                        <div v-if="recipe.memo" style="margin-bottom: 1rem; padding: 0.75rem; background: #f9fafb; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted); white-space: pre-wrap;">{{ recipe.memo }}</div>
                        <ul style="list-style:none;">
                            <li v-for="(item, idx) in recipe.items" :key="idx" style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; display:flex; justify-content:space-between;">
                                <span>{{ getIngName(item.ingredientId) }}</span>
                                <strong>{{ item.amount }} {{ getIngById(item.ingredientId)?.unit }}</strong>
                            </li>
                        </ul>
                    </div>
                    <div v-if="!showAddRecipeForm" class="card add-card" style="margin-bottom: 0;" @click="openAddRecipeForm">
                        <div class="add-card-icon">+</div>
                        <div class="add-card-text">新しいおかずを作成</div>
                    </div>
                </div>
                <div class="card" v-if="showAddRecipeForm" style="margin-top: 1.5rem;">
                    <h3 v-if="!editingRecipeId">新しいおかずを作成</h3>
                    <h3 v-else>おかずレシピを編集</h3>
                    <div class="form-group" style="margin-top: 1rem; margin-bottom: 0.5rem;">
                        <label>おかず名 <span style="color:var(--danger)">*</span></label>
                        <input type="text" v-model="newRecipe.name" placeholder="例: 定番の卵焼き"
                               @compositionupdate="onCompositionUpdate"
                               @compositionend="onCompositionEnd($event, newRecipe)"
                               @input="onInputName($event, newRecipe)">
                    </div>
                    <div class="form-group">
                        <label>ふりがな <span style="font-size:0.8rem; color:var(--muted); font-weight:normal;">(あいうえお順用)</span></label>
                        <input type="text" v-model="newRecipe.yomi" placeholder="例: ていばんのたまごやき">
                    </div>
                    <div class="form-group">
                        <label>レシピメモ (任意)</label>
                        <textarea v-model="newRecipe.memo" placeholder="簡単な作り方や、詰める時のコツなどをメモできます"></textarea>
                    </div>
                    
                    <div style="margin-top: 1.5rem;">
                        
                    <div class="form-group" style="margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem; background: #f0fdf4; padding: 1rem; border-radius: 8px;">
                        <label style="margin: 0; font-weight: 600; white-space: nowrap;">このレシピは何人前ですか？</label>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <input type="number" v-model.number="newRecipe.servings" min="1" step="1" style="width: 80px; text-align: right; font-size: 1.1rem; padding: 0.4rem;">
                            <span style="font-weight: 600;">人前</span>
                        </div>
                    </div>
                    
                    <label style="font-weight: 600; display:block; margin-bottom: 0.5rem;">{{ newRecipe.servings || 1 }}人前の材料構成</label>

                        <div class="flex-row" style="background:#f9fafb; padding:1rem; border-radius:12px;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <SearchableSelect 
                                    v-model="newRecipeItem.ingredientId" 
                                    :options="sortedIngredients.map(ing => ({ id: ing.id, name: `${ing.name} (${ing.unit})` }))" 
                                    placeholder="材料を検索・選択..." 
                                />
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="newRecipeItem.amount" min="0.1" step="0.1">
                                    <template v-if="newRecipeItem.ingredientId">
                                        <select v-if="getIngById(newRecipeItem.ingredientId)?.gPerUnit > 0 && getIngById(newRecipeItem.ingredientId)?.unit !== 'g'" v-model="newRecipeItem.inputUnit" style="width: 70px; padding: 0.3rem;">
                                            <option value="base">{{ getIngById(newRecipeItem.ingredientId)?.unit }}</option>
                                            <option value="g">g</option>
                                        </select>
                                        <span v-else style="font-size:0.9rem;">
                                            {{ getIngById(newRecipeItem.ingredientId)?.unit }}
                                        </span>
                                    </template>
                                </div>
                            </div>
                            <button class="btn btn-primary" @click="addIngredientToNewRecipe" style="padding:0.7rem 1rem;">追加</button>
                        </div>

                        <!-- Current building items -->
                        <div style="margin-top: 1rem;">
                            <div v-for="(item, idx) in newRecipe.items" :key="idx" class="menu-builder-item">
                                <strong>{{ getIngName(item.ingredientId) }}</strong>
                                <div style="display: flex; align-items: center; gap: 0.5rem; margin-left: 1rem;">
                                    <input type="number" v-model.number="item.amount" min="0.1" step="0.1" style="width: 80px; padding: 0.3rem; text-align: right;">
                                    <span>{{ getIngById(item.ingredientId)?.unit }}</span>
                                </div>
                                <button class="btn btn-danger" style="margin-left:auto; padding: 0.25rem 0.5rem;" @click="removeIngredientFromNewRecipe(idx)">✕</button>
                            </div>
                        </div>
                        
                        <div v-if="!editingRecipeId" style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                            <button class="btn btn-primary" style="flex: 1;" @click="addNewRecipe" :disabled="!newRecipe.name || newRecipe.items.length === 0">このおかずを保存</button>
                            <button class="btn" style="flex: 1; background: var(--surface); color: var(--text);" @click="cancelEditRecipe">閉じる</button>
                        </div>
                        <div v-else style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                            <button class="btn btn-primary" style="flex: 1;" @click="updateRecipe" :disabled="!newRecipe.name || newRecipe.items.length === 0">更新</button>
                            <button class="btn" style="flex: 1; background: var(--surface); color: var(--text);" @click="cancelEditRecipe">キャンセル</button>
                        </div>
                    </div>
                </div>
            </div>
            <!-- TAB: Menus -->
            <div v-if="currentTab === 'menus'" class="tab-pane">
                <header>
                    <h1>お弁当メニュー管理</h1>
                    <p>作成した「おかず」を組み合わせて、お弁当の全体メニューを作ります。</p>
                </header>


                <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
                    <label style="display:flex; align-items:center; gap:0.5rem; font-size:0.9rem; font-weight:600; color:var(--text-color); background: white; padding: 0.5rem 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); white-space: nowrap;">
                        並び順:
                        <select v-model="sortOrder" style="padding: 0.3rem 0.5rem; border-radius:4px; border:1px solid #d1d5db; background:#f9fafb;">
                            <option value="added">追加した順</option>
                            <option value="alphabetical">あいうえお順</option>
                        </select>
                    </label>
                </div>
                <!-- Existing Menus -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
                    <div class="card" v-for="menu in sortedMenus" :key="menu.id" style="margin-bottom: 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                            <h3>{{ menu.name }}</h3>
                            <div style="display:flex; gap: 0.5rem;">
                                <button class="btn" style="padding: 0.25rem 0.5rem; font-size: 0.85rem; background: var(--surface); color: var(--text);" @click="editMenu(menu)">編集</button>
                                <button class="btn btn-danger" style="padding: 0.25rem 0.75rem;" @click="removeMenu(menu.id)">削除</button>
                            </div>
                        </div>
                        <div v-if="menu.memo" style="margin-bottom: 1rem; padding: 0.75rem; background: #f9fafb; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted); white-space: pre-wrap;">{{ menu.memo }}</div>
                        <ul style="list-style:none;">
                            <li v-for="(item, idx) in menu.items" :key="idx" style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; display:flex; justify-content:space-between;">
                                <span>{{ getRecipeName(item.recipeId) }}</span>
                                <strong>{{ item.amount }} 人前分</strong>
                            </li>
                        </ul>
                    </div>

                    <div v-if="!showAddMenuForm" class="card add-card" style="margin-bottom: 0;" @click="openAddMenuForm">
                        <div class="add-card-icon">+</div>
                        <div class="add-card-text">新しいメニューを作成</div>
                    </div>
                </div>
                
                <div class="card" v-if="showAddMenuForm" style="margin-top: 1.5rem;">
                    <h3 v-if="!editingMenuId">新しいメニューを作成</h3>
                    <h3 v-else>お弁当メニューを編集</h3>
                    
                    <div class="form-group" style="margin-top: 1rem; margin-bottom: 0.5rem;">
                        <label>メニュー名</label>
                        <input type="text" v-model="newMenu.name" placeholder="例: 唐揚げ弁当"
                               @compositionupdate="onCompositionUpdate"
                               @compositionend="onCompositionEnd($event, newMenu)"
                               @input="onInputName($event, newMenu)">
                    </div>
                    <div class="form-group">
                        <label>ふりがな <span style="font-size:0.8rem; color:var(--muted); font-weight:normal;">(あいうえお順用)</span></label>
                        <input type="text" v-model="newMenu.yomi" placeholder="例: からあげべんとう">
                    </div>
                    <div class="form-group">
                        <label>メニューのメモ (任意)</label>
                        <textarea v-model="newMenu.memo" placeholder="お弁当のテーマや、誰用のお弁当かなどをメモできます"></textarea>
                    </div>
                    
                    <div style="margin-top: 1.5rem;">
                        <label style="font-weight: 600; display:block; margin-bottom: 0.5rem;">入れるおかず</label>
                        <div class="flex-row" style="background:#f9fafb; padding:1rem; border-radius:12px;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <SearchableSelect 
                                    v-model="newMenuItem.recipeId" 
                                    :options="sortedRecipes.map(r => ({ id: r.id, name: r.name }))" 
                                    placeholder="おかずを検索・選択..." 
                                />
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="newMenuItem.amount" min="1" step="1">
                                    <span style="font-size:0.9rem;">人前分</span>
                                </div>
                            </div>
                            <button class="btn btn-primary" @click="addRecipeToNewMenu" style="padding:0.7rem 1rem;">追加</button>
                        </div>

                        <!-- Current building items -->
                        <div style="margin-top: 1rem;">
                            <div v-for="(item, idx) in newMenu.items" :key="idx" class="menu-builder-item"
                                 draggable="true"
                                 @dragstart="onMenuDragStart($event, idx)"
                                 @dragover.prevent
                                 @dragenter.prevent
                                 @drop="onMenuDrop($event, idx)"
                                 style="cursor: grab;">
                                <div style="margin-right: 0.5rem; color: #9ca3af; cursor: grab;">≡</div>
                                <strong>{{ getRecipeName(item.recipeId) }}</strong>
                                <div style="display: flex; align-items: center; gap: 0.5rem; margin-left: 1rem;">
                                    <input type="number" v-model.number="item.amount" min="1" step="1" style="width: 80px; padding: 0.3rem; text-align: right;">
                                    <span>人前分</span>
                                </div>
                                <button class="btn btn-danger" style="margin-left:auto; padding: 0.25rem 0.5rem;" @click="removeRecipeFromNewMenu(idx)">✕</button>
                            </div>
                        </div>
                        
                        <div v-if="!editingMenuId" style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                            <button class="btn btn-primary" style="flex: 1;" @click="addNewMenu" :disabled="!newMenu.name || newMenu.items.length === 0">このメニューを保存</button>
                            <button class="btn" style="flex: 1; background: var(--surface); color: var(--text);" @click="cancelEditMenu">閉じる</button>
                        </div>
                        <div v-else style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                            <button class="btn btn-primary" style="flex: 1;" @click="updateMenu" :disabled="!newMenu.name || newMenu.items.length === 0">更新</button>
                            <button class="btn" style="flex: 1; background: var(--surface); color: var(--text);" @click="cancelEditMenu">キャンセル</button>
                        </div>
                    </div>
                </div>
            </div>


            <!-- TAB: Daily Production and Prep -->
            <div v-if="currentTab === 'daily'" class="tab-pane">
                <header class="no-print" style="display: flex; justify-content: space-between; align-items: flex-end;">
                    <div>
                        <h1>日々の作業・実績</h1>
                        <p>今日の製造実績の入力（在庫引き落とし）と、明日の仕込み計算を行います。</p>
                    </div>
                    <button class="btn" style="background: var(--surface); color: var(--text); padding: 0.5rem 1rem; margin-bottom: 1rem;" @click="printCalculation">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 0.25rem;"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
                        A4印刷・PDF保存
                    </button>
                </header>

                <div class="print-header" style="display: none;">
                    <h1>日々の作業・仕込みリスト</h1>
                </div>

                <div class="card" style="margin-bottom: 2rem; overflow-x: auto; padding-top: 1rem;">
                    <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                        <h3 style="margin: 0; margin-right: 1rem;">配達先別 個数表</h3>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <label style="font-weight: bold; margin-bottom: 0;">日付:</label>
                            <input type="text" v-model="bentoDestinations.date" placeholder="例: 7/30 (木)" style="width: 150px; padding: 0.25rem 0.5rem; font-size: 1rem; border: none; border-bottom: 2px solid #333; border-radius: 0; background: transparent; outline: none;">
                        </div>
                    </div>
                    
                    <table class="tally-table" style="width: 100%; border-collapse: collapse; text-align: center; border: 2px solid #333; margin-bottom: 1rem;">
                        <tbody>
                            <tr style="background: #f8fafc;">
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 1</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 2</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 3</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 4</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 5</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;"></th>
                            </tr>
                            <tr>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no1" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no2" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no3" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no4" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no5" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"></td>
                            </tr>
                            <tr style="background: #f8fafc;">
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">No, 6</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">本社</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">計</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">E</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">W</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">計</th>
                            </tr>
                            <tr>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.no6" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.honsha" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.5rem; font-size: 1.5rem; font-weight: bold; position: relative;">
                                    <div class="circled-number">{{ bentoSubtotal1 || '' }}</div>
                                </td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.e" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.w" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.5rem; font-size: 1.5rem; font-weight: bold; position: relative;">
                                    <div class="circled-number">{{ bentoSubtotal2 || '' }}</div>
                                </td>
                            </tr>
                            <tr style="background: #f8fafc;">
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500; font-size: 0.9rem;">ファミリア</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">はじめ</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">貴志川</th>
                                <th style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">計</th>
                                <th colspan="2" style="border: 1px solid #333; padding: 0.5rem; font-weight: 500;">合計</th>
                            </tr>
                            <tr>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.familia" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.hajime" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.25rem;"><input type="number" v-model.number="bentoDestinations.kishigawa" class="tally-input"></td>
                                <td style="border: 1px solid #333; padding: 0.5rem; font-size: 1.5rem; font-weight: bold; position: relative;">
                                    <div class="circled-number">{{ bentoSubtotal3 || '' }}</div>
                                </td>
                                <td colspan="2" style="border: 1px solid #333; padding: 0.5rem; font-size: 1.8rem; font-weight: bold; position: relative;">
                                    <div class="circled-number" style="min-width: 4rem;">{{ bentoGrandTotal || '' }}</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="card page-break" style="margin-bottom: 2rem;">
                    <h3>今日の製造と実績入力</h3>
                    <p class="no-print" style="font-size: 0.9rem; color: var(--muted); margin-bottom: 1rem;">今日作る予定のメニューを入力し、調理後に実際の使用量を入力して在庫を減らします。</p>
                    
                    <div class="no-print" style="margin-bottom: 1.5rem; background: #f8fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <div v-for="(plan, idx) in dailyPlanToday" :key="'today-'+plan.id" class="flex-row" style="margin-bottom: 0.5rem; align-items:center;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <select v-model="plan.menuId">
                                    <option value="">メニューを選択...</option>
                                    <option v-for="menu in sortedMenus" :key="menu.id" :value="menu.id">{{ menu.name }}</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="plan.peopleCount" min="1" step="1">
                                    <span style="font-size:0.9rem;">人分</span>
                                </div>
                            </div>
                            <button class="btn btn-danger" style="padding: 0.5rem 0.75rem;" @click="removeDailyPlanTodayItem(idx)">✕</button>
                        </div>
                        <button class="btn" style="background: white; border: 1px solid var(--border); width: 100%; color: var(--text);" @click="addDailyPlanTodayItem">＋ 今日の製造メニューを追加</button>
                    </div>

                    <div v-if="todayExpectedIngredientsByMenu.length > 0">
                        <div class="print-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
                            <div v-for="(grp, index) in todayExpectedIngredientsByMenu" :key="grp.id" :class="{'page-break': index > 0 && index % 2 === 0}" style="border: 1px solid #eee; padding: 1rem; border-radius: 8px;">
                                <h4 style="color: var(--primary-dark); margin-bottom: 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.5rem;">{{ grp.menu.name }} <span style="font-size: 0.9rem; font-weight: normal; color: var(--muted);">({{ grp.portions }} 人前分)</span></h4>
                                <div v-for="(recGrp, rIdx) in grp.recipes" :key="rIdx" class="print-recipe-group" style="margin-bottom: 1rem;">
                                    <div class="print-recipe-title" style="font-weight: 600; font-size: 0.95rem; background: #f8fafc; padding: 0.25rem 0.5rem; border-left: 3px solid var(--primary); margin-bottom: 0.5rem; color: var(--text);">
                                        {{ recGrp.recipe.name }}
                                    </div>
                                    <ul class="print-ingredient-list" style="list-style: none; padding: 0 0 0 0.5rem; margin: 0; display: flex; flex-direction: column; gap: 0.25rem;">
                                        <li v-for="item in recGrp.ingredients" :key="item.id" style="display: flex; justify-content: space-between; border-bottom: 1px dashed #e2e8f0; padding-bottom: 0.25rem;">
                                            <span style="font-weight: 600;">{{ item.name }}</span>
                                            <span style="color: var(--text);">{{ formatAmount(item.required, item.unit, item.gPerUnit) }}</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div class="no-print" style="margin-top: 2.5rem; text-align: center;">
                            <button class="btn btn-primary" style="padding: 1rem 2rem; font-size: 1.1rem; width: 100%; max-width: 400px; border-radius: 100px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);" @click="showActualsModal = true">
                                お弁当完成！（実績を入力して在庫を減らす）
                            </button>
                        </div>
                    </div>
                </div>

                <div class="card page-break">
                    <h3>明日の仕込み（おかずごと）</h3>
                    <p class="no-print" style="font-size: 0.9rem; color: var(--muted); margin-bottom: 1rem;">明日仕込む予定のおかず（レシピ）と人数を入力すると、必要な材料が計算されます。</p>
                    
                    <div class="no-print" style="margin-bottom: 1.5rem; background: #f8fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <div v-for="(plan, idx) in dailyPlanTomorrow" :key="'tom-'+plan.id" class="flex-row" style="margin-bottom: 0.5rem; align-items:center;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <select v-model="plan.recipeId">
                                    <option value="">おかずを選択...</option>
                                    <option v-for="recipe in sortedRecipes" :key="recipe.id" :value="recipe.id">{{ recipe.name }}</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="plan.peopleCount" min="1" step="1">
                                    <span style="font-size:0.9rem;">人分</span>
                                </div>
                            </div>
                            <button class="btn btn-danger" style="padding: 0.5rem 0.75rem;" @click="removeDailyPlanTomorrowItem(idx)">✕</button>
                        </div>
                        <button class="btn" style="background: white; border: 1px solid var(--border); width: 100%; color: var(--text);" @click="addDailyPlanTomorrowItem">＋ 明日仕込むおかずを追加</button>
                    </div>

                    <div v-if="tomorrowPrepRecipes.length > 0">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
                            <div v-for="grp in tomorrowPrepRecipes" :key="grp.recipe.id" style="border: 1px solid #eee; padding: 1rem; border-radius: 8px;">
                                <h4 style="color: var(--primary-dark); margin-bottom: 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.5rem;">{{ grp.recipe.name }} <span style="font-size: 0.9rem; font-weight: normal; color: var(--muted);">({{ grp.portions }} 人前分)</span></h4>
                                <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.25rem;">
                                    <li v-for="(amount, ingIdStr) in grp.ingredientsReq" :key="ingIdStr" style="display: flex; justify-content: space-between; border-bottom: 1px dashed #e2e8f0; padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600;">{{ getIngById(parseInt(ingIdStr))?.name }}</span>
                                        <span style="color: var(--text);">{{ formatAmount(amount, getIngById(parseInt(ingIdStr))?.unit, getIngById(parseInt(ingIdStr))?.gPerUnit) }}</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            <!-- TAB: Weekly Shopping -->

            <div v-if="currentTab === 'shopping'" class="tab-pane">
                <header>
                    <h1>週間仕入れリスト（お買い物リスト）</h1>
                    <p>1週間分の作る予定を入力すると、現在の在庫を差し引いて「買うべきもの」をリストアップします。</p>
                </header>
                
                <div class="card">
                    <h3>1. 仕入れ予定の入力</h3>
                    <div style="margin-top: 1rem;">
                        <div v-for="(plan, idx) in weeklyPlan" :key="plan.id" class="flex-row" style="background:#f9fafb; padding:0.75rem; border-radius:8px; margin-bottom: 0.5rem; align-items:center;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <select v-model="plan.menuId">
                                    <option value="">メニューを選択...</option>
                                    <option v-for="menu in sortedMenus" :key="menu.id" :value="menu.id">{{ menu.name }}</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="plan.peopleCount" min="1" step="1">
                                    <span style="font-size:0.9rem;">人分</span>
                                </div>
                            </div>
                            <button class="btn btn-danger" style="padding: 0.5rem 0.75rem;" @click="removeWeeklyPlanItem(idx)">✕</button>
                        </div>
                        <button class="btn" style="margin-top: 0.5rem; background: var(--primary-light); color: var(--primary-dark); width: 100%;" @click="addWeeklyPlanItem">予定を追加</button>
                    </div>
                </div>

                <div class="card">
                    <h3>2. お買い物リスト</h3>
                    <div v-if="weeklyShoppingList.length === 0" style="margin-top: 1rem; color: var(--text-muted);">
                        予定を追加すると、ここにリストが表示されます。
                    </div>
                    <div v-else style="overflow-x: auto; margin-top: 1rem;">
                        <table class="list-table">
                            <thead>
                                <tr>
                                    <th>材料</th>
                                    <th>1週間の必要量</th>
                                    <th>現在庫</th>
                                    <th>買うべき量</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in weeklyShoppingList" :key="item.id" :style="item.shortage > 0 ? 'background: #fff5f5;' : ''">
                                    <td style="font-weight: 600;">{{ item.name }}</td>
                                    <td>{{ formatAmount(item.required, item.unit, item.gPerUnit) }}</td>
                                    <td>{{ formatAmount(item.stock, item.unit, item.gPerUnit) }}</td>
                                    <td>
                                        <div v-if="item.shortage > 0">
                                            <div style="font-weight:bold; color: var(--danger); font-size: 1.1rem;">
                                                {{ item.hasPackage ? (item.buyPackages + ' ' + item.pkgUnit) : formatAmount(item.shortage, item.unit, item.gPerUnit) }}
                                            </div>
                                            <div v-if="item.hasPackage" style="font-size: 0.85rem; color: var(--text-muted);">
                                                (不足: {{ formatAmount(item.shortage, item.unit, item.gPerUnit) }})
                                            </div>
                                        </div>
                                        <div v-else style="color: var(--success); font-weight: bold;">
                                            ✅ 在庫十分
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Modal for Actuals Input -->
            <div v-if="showActualsModal" class="modal-overlay" @click.self="showActualsModal = false">
                <div class="modal-content" style="max-width: 800px; width: 95%;">
                    <h2 style="margin-bottom: 0.5rem;">実績の入力と在庫引き落とし</h2>
                    <p style="margin-bottom: 1.5rem;">今日使った全材料の合計量です。<br>実際の使用量を入力してから「確定」を押してください。</p>
                    
                    <div style="overflow-x: auto; max-height: 50vh; margin-bottom: 1.5rem;">
                        <table class="inventory-table">
                            <thead>
                                <tr>
                                    <th>材料名</th>
                                    <th>必要な量（予定合計）</th>
                                    <th>実際に使った量</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in todayExpectedIngredients" :key="item.id">
                                    <td style="font-weight: 600;">{{ item.name }}</td>
                                    <td>{{ formatAmount(item.required, item.unit, item.gPerUnit) }}</td>
                                    <td>
                                        <div style="display:flex; align-items:center; gap:0.5rem;">
                                            <input type="number" v-model.number="dailyActuals[item.id]" :placeholder="formatAmount(item.required, item.unit, item.gPerUnit, true)" step="0.1" style="width: 100px;">
                                            <span style="font-size: 0.9rem; color: var(--muted);">{{ item.unit }}</span>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-primary" style="flex: 1; padding: 1rem;" @click="deductStock">確定して在庫を減らす</button>
                        <button class="btn" style="flex: 1; background: var(--surface); color: var(--text); padding: 1rem;" @click="showActualsModal = false">キャンセル</button>
                    </div>
                </div>
            </div>

            <div v-if="currentTab === 'calendar'" class="tab-pane">
                <header class="no-print" style="display: flex; justify-content: space-between; align-items: flex-end;">
                    <div>
                        <h1>月間配送カレンダー</h1>
                        <p>PCで数値を入力し、A4タテで3列に並んだカレンダーを印刷できます。</p>
                    </div>
                    <button class="btn" style="background: var(--surface); color: var(--text); padding: 0.5rem 1rem; margin-bottom: 1rem;" onclick="window.print()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 0.25rem;"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
                        A4印刷・PDF保存
                    </button>
                </header>

                <div class="print-header" style="display: none;">
                    <h1>月間配送カレンダー</h1>
                </div>

                <!-- Monthly Calendar Print Section -->
                <div class="card page-break" style="margin-bottom: 2rem;">
                    <div class="no-print" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div>
                            <h3 style="margin-bottom: 0.25rem;">月間配送カレンダー (PC入力・印刷用)</h3>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <button class="btn" @click="prevCalendarMonth">◀ 前月</button>
                            <strong style="font-size: 1.2rem;">{{ calendarYear }}年 {{ calendarMonth + 1 }}月</strong>
                            <button class="btn" @click="nextCalendarMonth">次月 ▶</button>
                        </div>
                    </div>
                    
                    <div v-for="copy in 2" :key="copy" :class="{ 'print-only': copy === 2 }" :style="{ marginBottom: copy === 1 ? '2rem' : '0' }">
                        <div class="print-calendar-container" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;">
                            <div v-for="dest in ['ファミリア', 'はじめ', '貴志川', '合計']" :key="dest" style="min-width: 0;">
                                <h4 style="text-align: center; margin-bottom: 0.5rem; font-size: 1.2rem;">{{ dest }}</h4>
                                <table style="width: 100%; border-collapse: collapse; text-align: center; border: 2px solid #333; table-layout: fixed;">
                                    <thead>
                                        <tr style="background: #f8fafc;">
                                            <th style="border: 1px solid #333; padding: 2px 0; font-size: 0.8rem;">月</th>
                                            <th style="border: 1px solid #333; padding: 2px 0; font-size: 0.8rem;">火</th>
                                            <th style="border: 1px solid #333; padding: 2px 0; font-size: 0.8rem;">水</th>
                                            <th style="border: 1px solid #333; padding: 2px 0; font-size: 0.8rem;">木</th>
                                            <th style="border: 1px solid #333; padding: 2px 0; font-size: 0.8rem;">金</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="(week, wIdx) in calendarWeeks" :key="wIdx">
                                            <td class="calendar-cell" v-for="d in 5" :key="d" style="border: 1px solid #333; height: 50px; vertical-align: top; padding: 2px;">
                                                <template v-if="week[d-1] && week[d-1].isCurrentMonth">
                                                    <div style="text-align: left; font-size: 0.7rem; color: #333; line-height: 1;">{{ week[d-1].dateNum }}</div>
                                                    <div style="margin-top: 2px; text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;">
                                                        <template v-if="dest === '合計'">
                                                            <div class="calendar-input" style="width: 100%; min-width: 0; height: 30px; line-height: 30px; text-align: center; font-size: 1.2rem; font-weight: bold; border: none; background: transparent; color: var(--primary);">
                                                                {{ 
                                                                    ((calendarData[calendarYear + '-' + (calendarMonth+1) + '-' + week[d-1].dateNum + '-ファミリア'] || 0) + 
                                                                    (calendarData[calendarYear + '-' + (calendarMonth+1) + '-' + week[d-1].dateNum + '-はじめ'] || 0) + 
                                                                    (calendarData[calendarYear + '-' + (calendarMonth+1) + '-' + week[d-1].dateNum + '-貴志川'] || 0)) || ''
                                                                }}
                                                            </div>
                                                        </template>
                                                        <template v-else>
                                                            <input class="calendar-input" type="number" v-model.number="calendarData[calendarYear + '-' + (calendarMonth+1) + '-' + week[d-1].dateNum + '-' + dest]" style="width: 100%; min-width: 0; height: 30px; text-align: center; font-size: 1.2rem; font-weight: bold; border: none; background: transparent; outline: none; padding: 0; box-sizing: border-box;">
                                                        </template>
                                                    </div>
                                                </template>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <hr class="print-only-hr" v-if="copy === 1" style="margin-top: 3rem; border: none; border-top: 1px dashed #ccc;" />
                    </div>
                </div>
            </div>
        </main>
    </template>
  </div>
</template>