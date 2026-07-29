<template>
    <div class="searchable-select" ref="container">
        <input 
            type="text" 
            v-model="searchQuery" 
            @focus="isOpen = true"
            @input="handleInput"
            :placeholder="placeholder"
            class="search-input"
        >
        <div v-if="isOpen" class="dropdown-list">
            <div 
                v-for="option in filteredOptions" 
                :key="option.id" 
                class="dropdown-item"
                @click="selectOption(option)"
            >
                {{ option.name }}
            </div>
            <div v-if="filteredOptions.length === 0" class="dropdown-item empty">
                見つかりません
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';

const props = defineProps({
    modelValue: {
        type: [String, Number],
        default: ''
    },
    options: {
        type: Array,
        required: true
    },
    placeholder: {
        type: String,
        default: '検索...'
    }
});

const emit = defineEmits(['update:modelValue']);

const isOpen = ref(false);
const searchQuery = ref('');
const container = ref(null);

// Initialize search query if modelValue exists
watch(() => props.modelValue, (newVal) => {
    if (newVal !== '' && newVal !== null && newVal !== undefined) {
        const selected = props.options.find(opt => opt.id === newVal);
        if (selected) {
            searchQuery.value = selected.name;
        }
    } else {
        searchQuery.value = '';
    }
}, { immediate: true });

const filteredOptions = computed(() => {
    if (!searchQuery.value) return props.options;
    // If the searchQuery perfectly matches the selected option, show all
    const selected = props.options.find(opt => opt.id === props.modelValue);
    if (selected && selected.name === searchQuery.value) {
        return props.options;
    }
    const normalize = (str) => {
        if (!str) return '';
        // Convert Katakana to Hiragana
        return str.replace(/[\u30a1-\u30f6]/g, function(match) {
            return String.fromCharCode(match.charCodeAt(0) - 0x60);
        }).toLowerCase();
    };
    const query = normalize(searchQuery.value);
    return props.options.filter(opt => normalize(opt.name).includes(query));
});

const selectOption = (option) => {
    searchQuery.value = option.name;
    emit('update:modelValue', option.id);
    isOpen.value = false;
};

const handleInput = () => {
    isOpen.value = true;
    emit('update:modelValue', ''); // Clear selection when typing
};

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
    if (container.value && !container.value.contains(event.target)) {
        isOpen.value = false;
        // If they didn't select anything valid, clear or reset
        const selected = props.options.find(opt => opt.id === props.modelValue);
        if (selected) {
            searchQuery.value = selected.name;
        } else {
            searchQuery.value = '';
        }
    }
};

onMounted(() => {
    document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.searchable-select {
    position: relative;
    width: 100%;
}

.search-input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    font-size: 1rem;
    box-sizing: border-box;
}
.search-input:focus {
    outline: none;
    border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.dropdown-list {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    z-index: 1000;
    margin-top: 4px;
}

.dropdown-item {
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: background 0.2s;
    color: #1f2937;
}

.dropdown-item:hover {
    background: #d1fae5;
    color: #059669;
}

.dropdown-item.empty {
    color: #6b7280;
    cursor: default;
}
.dropdown-item.empty:hover {
    background: white;
}
</style>
