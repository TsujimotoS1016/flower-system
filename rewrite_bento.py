import re
import sys

with open('/Users/tsujimotoshonosuke/Test/フラファーシステム/bento_inventory.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Navigation
old_nav = """            <ul class="nav-links">
                <li :class="{ active: currentTab === 'calc' }" @click="currentTab = 'calc'">計算・買い物</li>
                <li :class="{ active: currentTab === 'inventory' }" @click="currentTab = 'inventory'">在庫・材料</li>
                <li :class="{ active: currentTab === 'menus' }" @click="currentTab = 'menus'">メニュー</li>
            </ul>"""
new_nav = """            <ul class="nav-links">
                <li :class="{ active: currentTab === 'calc' }" @click="currentTab = 'calc'">計算・買い物</li>
                <li :class="{ active: currentTab === 'inventory' }" @click="currentTab = 'inventory'">在庫・材料</li>
                <li :class="{ active: currentTab === 'recipes' }" @click="currentTab = 'recipes'">おかずレシピ</li>
                <li :class="{ active: currentTab === 'menus' }" @click="currentTab = 'menus'">お弁当メニュー</li>
            </ul>"""
html = html.replace(old_nav, new_nav)

# 2. Add Recipes Tab before Menus Tab
recipes_tab = """
            <!-- TAB: Recipes -->
            <div v-if="currentTab === 'recipes'" class="tab-pane">
                <header>
                    <h1>おかずレシピ管理</h1>
                    <p>お弁当に入る「おかず（卵焼き等）」と、その1人前に必要な材料を登録します。</p>
                </header>

                <div class="card">
                    <h3>➕ 新しいおかずを作成</h3>
                    <div class="form-group" style="margin-top: 1rem;">
                        <label>おかず名</label>
                        <input type="text" v-model="newRecipe.name" placeholder="例: 定番の卵焼き">
                    </div>
                    <div class="form-group">
                        <label>レシピメモ (任意)</label>
                        <textarea v-model="newRecipe.memo" placeholder="簡単な作り方や、詰める時のコツなどをメモできます"></textarea>
                    </div>
                    
                    <div style="margin-top: 1.5rem;">
                        <label style="font-weight: 600; display:block; margin-bottom: 0.5rem;">1人前の材料構成</label>
                        <div class="flex-row" style="background:#f9fafb; padding:1rem; border-radius:12px;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <select v-model="newRecipeItem.ingredientId">
                                    <option value="">材料を選択...</option>
                                    <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">{{ ing.name }} ({{ ing.unit }})</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1; margin-bottom:0;">
                                <div style="display:flex; align-items:center; gap:0.5rem;">
                                    <input type="number" v-model.number="newRecipeItem.amount" min="0.1" step="0.1">
                                    <span style="font-size:0.9rem;" v-if="newRecipeItem.ingredientId">
                                        {{ getIngById(newRecipeItem.ingredientId)?.unit }}
                                    </span>
                                </div>
                            </div>
                            <button class="btn btn-primary" @click="addIngredientToNewRecipe" style="padding:0.7rem 1rem;">追加</button>
                        </div>

                        <!-- Current building items -->
                        <div style="margin-top: 1rem;">
                            <div v-for="(item, idx) in newRecipe.items" :key="idx" class="menu-builder-item">
                                <strong>{{ getIngName(item.ingredientId) }}</strong>
                                <span>{{ item.amount }} {{ getIngById(item.ingredientId)?.unit }}</span>
                                <button class="btn btn-danger" style="margin-left:auto; padding: 0.25rem 0.5rem;" @click="removeIngredientFromNewRecipe(idx)">✕</button>
                            </div>
                        </div>
                        
                        <button class="btn btn-primary" style="margin-top: 1.5rem; width: 100%;" @click="addNewRecipe" :disabled="!newRecipe.name || newRecipe.items.length === 0">
                            このおかずを保存
                        </button>
                    </div>
                </div>

                <!-- Existing Recipes -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
                    <div class="card" v-for="recipe in recipes" :key="recipe.id" style="margin-bottom: 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                            <h3>{{ recipe.name }}</h3>
                            <button class="btn btn-danger" style="padding: 0.25rem 0.75rem;" @click="removeRecipe(recipe.id)">削除</button>
                        </div>
                        <div v-if="recipe.memo" style="margin-bottom: 1rem; padding: 0.75rem; background: #f9fafb; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted); white-space: pre-wrap;">{{ recipe.memo }}</div>
                        <ul style="list-style:none;">
                            <li v-for="(item, idx) in recipe.items" :key="idx" style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; display:flex; justify-content:space-between;">
                                <span>{{ getIngName(item.ingredientId) }}</span>
                                <strong>{{ item.amount }} {{ getIngById(item.ingredientId)?.unit }}</strong>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
"""
menus_tab_start = html.find("            <!-- TAB: Menus -->")
html = html[:menus_tab_start] + recipes_tab + html[menus_tab_start:]

# 3. Replace Menus Tab UI
old_menus_tab = html[html.find("            <!-- TAB: Menus -->"):html.find("        </main>")]
new_menus_tab = """            <!-- TAB: Menus -->
            <div v-if="currentTab === 'menus'" class="tab-pane">
                <header>
                    <h1>お弁当メニュー管理</h1>
                    <p>作成した「おかず」を組み合わせて、お弁当の全体メニューを作ります。</p>
                </header>

                <div class="card">
                    <h3>➕ 新しいメニューを作成</h3>
                    <div class="form-group" style="margin-top: 1rem;">
                        <label>メニュー名</label>
                        <input type="text" v-model="newMenu.name" placeholder="例: ハンバーグ弁当">
                    </div>
                    <div class="form-group">
                        <label>お弁当メモ (任意)</label>
                        <textarea v-model="newMenu.memo" placeholder="お弁当全体のテーマや、詰める順番などをメモできます"></textarea>
                    </div>
                    
                    <div style="margin-top: 1.5rem;">
                        <label style="font-weight: 600; display:block; margin-bottom: 0.5rem;">入れるおかず</label>
                        <div class="flex-row" style="background:#f9fafb; padding:1rem; border-radius:12px;">
                            <div class="form-group" style="flex: 2; margin-bottom:0;">
                                <select v-model="newMenuItem.recipeId">
                                    <option value="">おかずを選択...</option>
                                    <option v-for="recipe in recipes" :key="recipe.id" :value="recipe.id">{{ recipe.name }}</option>
                                </select>
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
                            <div v-for="(item, idx) in newMenu.items" :key="idx" class="menu-builder-item">
                                <strong>{{ getRecipeName(item.recipeId) }}</strong>
                                <span>{{ item.amount }} 人前分</span>
                                <button class="btn btn-danger" style="margin-left:auto; padding: 0.25rem 0.5rem;" @click="removeRecipeFromNewMenu(idx)">✕</button>
                            </div>
                        </div>
                        
                        <button class="btn btn-primary" style="margin-top: 1.5rem; width: 100%;" @click="addNewMenu" :disabled="!newMenu.name || newMenu.items.length === 0">
                            このメニューを保存
                        </button>
                    </div>
                </div>

                <!-- Existing Menus -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
                    <div class="card" v-for="menu in menus" :key="menu.id" style="margin-bottom: 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                            <h3>{{ menu.name }}</h3>
                            <button class="btn btn-danger" style="padding: 0.25rem 0.75rem;" @click="removeMenu(menu.id)">削除</button>
                        </div>
                        <div v-if="menu.memo" style="margin-bottom: 1rem; padding: 0.75rem; background: #f9fafb; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted); white-space: pre-wrap;">{{ menu.memo }}</div>
                        <ul style="list-style:none;">
                            <li v-for="(item, idx) in menu.items" :key="idx" style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; display:flex; justify-content:space-between;">
                                <span>{{ getRecipeName(item.recipeId) }}</span>
                                <strong>{{ item.amount }} 人前分</strong>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>\n"""
html = html.replace(old_menus_tab, new_menus_tab)

# 4. Replace setup script logic
old_script = html[html.find("        const { createApp"):html.find("        }).mount('#app');")]

new_script = """        const { createApp, ref, computed, watch, onMounted } = Vue;

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

                // 在庫管理ロジック
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
                const removeIngredient = (id) => {
                    ingredients.value = ingredients.value.filter(i => i.id !== id);
                    recipes.value.forEach(r => {
                        r.items = r.items.filter(item => item.ingredientId !== id);
                    });
                };

                // レシピ管理ロジック
                const newRecipe = ref({ name: '', memo: '', items: [] });
                const newRecipeItem = ref({ ingredientId: '', amount: 1 });
                
                const getIngById = (id) => ingredients.value.find(i => i.id === id);
                const getIngName = (id) => {
                    const ing = getIngById(id);
                    return ing ? ing.name : '不明';
                };

                const addIngredientToNewRecipe = () => {
                    if (!newRecipeItem.value.ingredientId) return;
                    newRecipe.value.items.push({...newRecipeItem.value});
                    newRecipeItem.value = { ingredientId: '', amount: 1 };
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
                const removeRecipe = (id) => {
                    recipes.value = recipes.value.filter(r => r.id !== id);
                    menus.value.forEach(m => {
                        m.items = m.items.filter(item => item.recipeId !== id);
                    });
                };

                // メニュー管理ロジック
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
                const removeMenu = (id) => {
                    menus.value = menus.value.filter(m => m.id !== id);
                };

                return {
                    currentTab, ingredients, recipes, menus, selectedMenuId, peopleCount, selectedMenu, 
                    calculationResults, shoppingList, sufficientList, formatAmount, 
                    newIngredient, addIngredient, removeIngredient,
                    newRecipe, newRecipeItem, addNewRecipe, removeRecipe, addIngredientToNewRecipe, removeIngredientFromNewRecipe,
                    newMenu, newMenuItem, addNewMenu, removeMenu, addRecipeToNewMenu, removeRecipeFromNewMenu, 
                    getIngById, getIngName, getRecipeById, getRecipeName
                };
"""

html = html.replace(old_script, new_script)

with open('/Users/tsujimotoshonosuke/Test/フラファーシステム/bento_inventory.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done")
