const { createApp, ref, computed, watch, onMounted } = Vue;

        createApp({
            setup() {
                const currentTab = ref('calc');
                
                const ingredients = ref([]);
                const recipes = ref([]);
                const menus = ref([]);
                
                const selectedMenuId = ref('');
                const peopleCount = ref(1);

                // 初期データのロード
                onMounted(() => {
                    const savedIng = localStorage.getItem('bento_ingredients');
                    const savedRec = localStorage.getItem('bento_recipes');
                    const savedMen = localStorage.getItem('bento_menus');
                    
                    const defaultIngredients = [
                        { id: 1, name: 'にんじん', unit: '本', gPerUnit: 150, stock: 0.5 },
                        { id: 2, name: 'じゃがいも', unit: '個', gPerUnit: 150, stock: 2 },
                        { id: 3, name: '玉ねぎ', unit: '個', gPerUnit: 200, stock: 1 },
                        { id: 4, name: '豚肉', unit: 'g', gPerUnit: 1, stock: 100 },
                        { id: 5, name: '卵', unit: '個', gPerUnit: 0, stock: 3 }, // 換算なし
                        { id: 6, name: '唐揚げ用鶏肉', unit: 'g', gPerUnit: 1, stock: 500 },
                        { id: 7, name: 'ブロッコリー', unit: '株', gPerUnit: 250, stock: 0 },
                        { id: 8, name: 'キャベツ', unit: '個', gPerUnit: 1000, stock: 0 },
                        { id: 9, name: 'ズッキーニ', unit: '本', gPerUnit: 200, stock: 0 },
                        { id: 10, name: 'ゴーヤ', unit: '本', gPerUnit: 250, stock: 0 },
                        { id: 11, name: 'ミニトマト', unit: '個', gPerUnit: 0, stock: 0 },
                        { id: 12, name: 'なす', unit: '本', gPerUnit: 80, stock: 0 }
                    ];

                    if (savedIng) {
                        let parsed = JSON.parse(savedIng);
                        const tomato = parsed.find(i => i.name === 'トマト');
                        if (tomato) {
                            tomato.name = 'ミニトマト';
                            tomato.gPerUnit = 0;
                        }
                        defaultIngredients.forEach(defIng => {
                            if (!parsed.find(i => i.name === defIng.name)) {
                                parsed.push(defIng);
                            }
                        });
                        ingredients.value = parsed;
                    } else {
                        ingredients.value = defaultIngredients;
                    }

                    if (savedRec) {
                        recipes.value = JSON.parse(savedRec);
                    }
                    if (savedMen) {
                        menus.value = JSON.parse(savedMen);
                    }

                    // Migration logic
                    if (savedMen && !savedRec) {
                        const oldMenus = JSON.parse(savedMen);
                        const migratedRecipes = [];
                        const migratedMenus = [];
                        
                        oldMenus.forEach(oldMenu => {
                            const recipeId = oldMenu.id;
                            migratedRecipes.push({
                                id: recipeId,
                                name: oldMenu.name + 'のおかずセット',
                                memo: oldMenu.memo,
                                items: oldMenu.items
                            });
                            migratedMenus.push({
                                id: oldMenu.id,
                                name: oldMenu.name,
                                memo: '',
                                items: [{ recipeId: recipeId, amount: 1 }]
                            });
                        });
                        recipes.value = migratedRecipes;
                        menus.value = migratedMenus;
                        localStorage.setItem('bento_recipes', JSON.stringify(recipes.value));
                        localStorage.setItem('bento_menus', JSON.stringify(menus.value));
                    } else if (!savedRec && !savedMen) {
                        // Default Data
                        recipes.value = [
                            {
                                id: 101,
                                name: '定番の肉じゃが',
                                memo: '豚肉は炒めてから野菜と煮込む。',
                                items: [
                                    { ingredientId: 4, amount: 60 },
                                    { ingredientId: 2, amount: 0.5 },
                                    { ingredientId: 1, amount: 0.2 },
                                    { ingredientId: 3, amount: 0.25 }
                                ]
                            },
                            {
                                id: 102,
                                name: '鶏の唐揚げ',
                                memo: '前日の夜から下味をつけておく。',
                                items: [{ ingredientId: 6, amount: 120 }]
                            },
                            {
                                id: 103,
                                name: '甘い卵焼き',
                                memo: '卵焼き1人前。',
                                items: [{ ingredientId: 5, amount: 0.5 }]
                            },
                            {
                                id: 104,
                                name: 'ブロッコリーの塩茹で',
                                memo: '彩りに。',
                                items: [{ ingredientId: 7, amount: 0.1 }]
                            }
                        ];
                        menus.value = [
                            { 
                                id: 201, 
                                name: '肉じゃがメイン弁当',
                                memo: '肉じゃがをドーンと入れる。',
                                items: [{ recipeId: 101, amount: 1 }]
                            },
                            { 
                                id: 202, 
                                name: '唐揚げ＆卵焼き弁当',
                                memo: '定番のお弁当！',
                                items: [
                                    { recipeId: 102, amount: 1 },
                                    { recipeId: 103, amount: 1 },
                                    { recipeId: 104, amount: 1 }
                                ]
                            }
                        ];
                    }
                });

                watch(ingredients, (newVal) => localStorage.setItem('bento_ingredients', JSON.stringify(newVal)), { deep: true });
                watch(recipes, (newVal) => localStorage.setItem('bento_recipes', JSON.stringify(newVal)), { deep: true });
                watch(menus, (newVal) => localStorage.setItem('bento_menus', JSON.stringify(newVal)), { deep: true });

                const selectedMenu = computed(() => menus.value.find(m => m.id === selectedMenuId.value));

                const calculationResults = computed(() => {
                    if (!selectedMenu.value) return [];
                    
                    const requiredMap = new Map();
                    
                    selectedMenu.value.items.forEach(menuItem => {
                        const recipe = recipes.value.find(r => r.id === menuItem.recipeId);
                        if (!recipe) return;
                        
                        recipe.items.forEach(recipeItem => {
                            const ingId = recipeItem.ingredientId;
                            const amount = recipeItem.amount * menuItem.amount; 
                            if (requiredMap.has(ingId)) {
                                requiredMap.set(ingId, requiredMap.get(ingId) + amount);
                            } else {
                                requiredMap.set(ingId, amount);
                            }
                        });
                    });
                    
                    const results = [];
                    for (const [ingId, amountPerPerson] of requiredMap.entries()) {
                        const ing = ingredients.value.find(i => i.id === ingId);
                        if (!ing) continue;
                        
                        const required = amountPerPerson * peopleCount.value;
                        const missing = Math.max(0, required - ing.stock);
                        
                        let buyPkg = 0;
                        if (ing.hasPackage && ing.pkgAmount > 0) {
                            buyPkg = Math.ceil(missing / ing.pkgAmount);
                        }
                        
                        results.push({
                            id: ing.id,
                            name: ing.name,
                            unit: ing.unit,
                            gPerUnit: ing.gPerUnit,
                            hasPackage: ing.hasPackage,
                            pkgUnit: ing.pkgUnit,
                            pkgAmount: ing.pkgAmount,
                            stock: ing.stock,
                            required,
                            missing,
                            buyPkg
                        });
                    }
                    return results;
                });

                const shoppingList = computed(() => calculationResults.value.filter(i => i.missing > 0));
                const sufficientList = computed(() => calculationResults.value.filter(i => i.missing === 0));

                const formatAmount = (amount, unit, gPerUnit) => {
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
                        unit: newIngredient.value.unit,
                        gPerUnit: finalGPerUnit,
                        hasPackage: newIngredient.value.hasPackage,
                        pkgUnit: newIngredient.value.pkgUnit,
                        pkgAmount: finalPkgAmount,
                        stock: finalStock
                    });
                    newIngredient.value = { name: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 };
                };
                
                const editIngredient = (ing) => {
                    editingIngredientId.value = ing.id;
                    newIngredient.value = { 
                        ...ing, 
                        pkgAmountUnit: ing.pkgAmountUnit || ing.unit,
                        displayStock: ing.hasPackage ? (ing.stock / ing.pkgAmount) : ing.stock
                    };
                    // スクロールして一番上に移動
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                };

                const cancelEditIngredient = () => {
                    editingIngredientId.value = null;
                    newIngredient.value = { name: '', unit: '個', gPerUnit: 100, hasPackage: false, pkgUnit: '袋', pkgAmount: 30, pkgAmountUnit: '個', displayStock: 0 };
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
                const newRecipe = ref({ name: '', memo: '', items: [] });
                const newRecipeItem = ref({ ingredientId: '', amount: 1, inputUnit: 'base' });
                watch(() => newRecipeItem.value.ingredientId, () => { newRecipeItem.value.inputUnit = 'base'; });
                
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
                        memo: newRecipe.value.memo,
                        items: [...newRecipe.value.items]
                    });
                    newRecipe.value = { name: '', memo: '', items: [] };
                };
                
                const editRecipe = (recipe) => {
                    editingRecipeId.value = recipe.id;
                    newRecipe.value = { 
                        name: recipe.name,
                        memo: recipe.memo,
                        items: JSON.parse(JSON.stringify(recipe.items))
                    };
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                };

                const cancelEditRecipe = () => {
                    editingRecipeId.value = null;
                    newRecipe.value = { name: '', memo: '', items: [] };
                };

                const updateRecipe = () => {
                    if (!newRecipe.value.name || newRecipe.value.items.length === 0 || !editingRecipeId.value) return;
                    const index = recipes.value.findIndex(r => r.id === editingRecipeId.value);
                    if (index !== -1) {
                        recipes.value[index] = {
                            id: editingRecipeId.value,
                            name: newRecipe.value.name,
                            memo: newRecipe.value.memo,
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
                const newMenu = ref({ name: '', memo: '', items: [] });
                const newMenuItem = ref({ recipeId: '', amount: 1 });
                
                const getRecipeById = (id) => recipes.value.find(r => r.id === id);
                const getRecipeName = (id) => {
                    const r = getRecipeById(id);
                    return r ? r.name : '不明';
                };

                const addRecipeToNewMenu = () => {
                    if (!newMenuItem.value.recipeId) return;
                    newMenu.value.items.push({...newMenuItem.value});
                    newMenuItem.value = { recipeId: '', amount: 1 };
                };
                const removeRecipeFromNewMenu = (idx) => {
                    newMenu.value.items.splice(idx, 1);
                };
                const addNewMenu = () => {
                    if (!newMenu.value.name || newMenu.value.items.length === 0) return;
                    menus.value.push({
                        id: Date.now(),
                        name: newMenu.value.name,
                        memo: newMenu.value.memo,
                        items: [...newMenu.value.items]
                    });
                    newMenu.value = { name: '', memo: '', items: [] };
                };

                const editMenu = (menu) => {
                    editingMenuId.value = menu.id;
                    newMenu.value = { 
                        name: menu.name,
                        memo: menu.memo,
                        items: JSON.parse(JSON.stringify(menu.items))
                    };
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                };

                const cancelEditMenu = () => {
                    editingMenuId.value = null;
                    newMenu.value = { name: '', memo: '', items: [] };
                };

                const updateMenu = () => {
                    if (!newMenu.value.name || newMenu.value.items.length === 0 || !editingMenuId.value) return;
                    const index = menus.value.findIndex(m => m.id === editingMenuId.value);
                    if (index !== -1) {
                        menus.value[index] = {
                            id: editingMenuId.value,
                            name: newMenu.value.name,
                            memo: newMenu.value.memo,
                            items: [...newMenu.value.items]
                        };
                    }
                    cancelEditMenu();
                };

                const removeMenu = (id) => {
                    menus.value = menus.value.filter(m => m.id !== id);
                };

                // 週間仕入れロジック
                const weeklyPlan = ref([{ id: Date.now(), menuId: '', peopleCount: 30 }]);
                
                const addWeeklyPlanItem = () => {
                    weeklyPlan.value.push({ id: Date.now(), menuId: '', peopleCount: 30 });
                };
                const removeWeeklyPlanItem = (idx) => {
                    weeklyPlan.value.splice(idx, 1);
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

                return {
                    currentTab, ingredients, recipes, menus, selectedMenuId, peopleCount, selectedMenu, 
                    calculationResults, shoppingList, sufficientList, formatAmount, 
                    newIngredient, addIngredient, removeIngredient, editingIngredientId, editIngredient, cancelEditIngredient, updateIngredient,
                    newRecipe, newRecipeItem, addNewRecipe, removeRecipe, addIngredientToNewRecipe, removeIngredientFromNewRecipe, editingRecipeId, editRecipe, cancelEditRecipe, updateRecipe,
                    newMenu, newMenuItem, addNewMenu, removeMenu, addRecipeToNewMenu, removeRecipeFromNewMenu, editingMenuId, editMenu, cancelEditMenu, updateMenu, 
                    weeklyPlan, addWeeklyPlanItem, removeWeeklyPlanItem, weeklyShoppingList,
                    getIngById, getIngName, getRecipeById, getRecipeName, consumeStock
                };
            }
        }).mount('#app');