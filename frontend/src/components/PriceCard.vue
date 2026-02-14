<template>
  <view class="price-card">
    <view class="card-header">
      <text class="card-icon">🏷️</text>
      <text class="card-title">AI 定价建议</text>
    </view>
    
    <swiper 
      class="price-swiper" 
      :current="currentIndex" 
      circular
      previous-margin="220rpx" 
      next-margin="220rpx"
      @change="onSwiperChange"
    >
      <swiper-item v-for="(item, index) in priceOptions" :key="index" class="swiper-item-wrapper">
        <view 
          class="price-card-inner" 
          :class="[currentIndex === index ? 'active-card' : 'inactive-card']"
          @click="currentIndex = index"
        >
          <text class="price-tag" :class="`tag-${item.color}`">{{ item.label }}</text>
          <view class="price-val-row">
            <text class="currency" :class="`text-${item.color}`">¥</text>
            <input 
              v-if="isEditing && currentIndex === index"
              class="amount-input"
              :class="`text-${item.color}`"
              type="digit"
              :value="item.price"
              @input="(e) => onInput(e, item.key)"
              :focus="true"
            />
            <text v-else class="amount" :class="`text-${item.color}`">{{ item.price }}</text>
          </view>
          <text class="price-desc">{{ item.desc }}</text>
        </view>
      </swiper-item>
    </swiper>
    
    <view class="card-footer">
      <view 
        class="action-btn" 
        :class="`btn-${currentPricing.color}`"
        @click="handleMainAction"
      >
        <text class="btn-text">{{ isEditing ? '确认调整' : `采纳${currentPricing.label}价` }}</text>
      </view>
      <view class="action-row-secondary">
        <view class="action-btn btn-outline" @click="toggleEdit">
          <text class="btn-text-outline">{{ isEditing ? '取消调整' : '手动调整' }}</text>
        </view>
        <view class="action-btn btn-ghost" @click="$emit('reject')">
          <text class="btn-text-ghost">不合适</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  pricing: {
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }
}>()
const emit = defineEmits<{ adopt: [price: number]; reject: []; adjust: [] }>()

const currentIndex = ref(1) // Default to Suggested (index 1)
const isEditing = ref(false)
const localPricing = ref({ ...props.pricing })

// Sync local pricing if props update
watch(() => props.pricing, (newVal) => {
  localPricing.value = { ...newVal }
}, { deep: true })

const priceOptions = computed(() => [
  { label: '保守', key: 'conservative_price', price: localPricing.value.conservative_price, desc: '快速出租', color: 'green' },
  { label: '推荐', key: 'suggested_price', price: localPricing.value.suggested_price, desc: '收益最大化', color: 'blue' },
  { label: '激进', key: 'aggressive_price', price: localPricing.value.aggressive_price, desc: '利润优先', color: 'orange' },
])

const currentPricing = computed(() => priceOptions.value[currentIndex.value])

function onSwiperChange(e: any) {
  currentIndex.value = e.detail.current
  isEditing.value = false // Exit edit mode on swipe
}

function toggleEdit() {
  isEditing.value = !isEditing.value
}

function handleMainAction() {
  if (isEditing.value) {
    // Confirm edit (exit edit mode but do not submit)
    isEditing.value = false
  } else {
    // Adopt current price (submit)
    emit('adopt', Number(currentPricing.value.price))
  }
}

function onInput(e: any, key: string) {
    let val = e.detail && e.detail.value
    if (val === undefined) {
        val = e.target ? e.target.value : ''
    }
    // @ts-ignore
    localPricing.value[key] = val
}
</script>

<style scoped lang="scss">
.price-card {
  background: #fff;
  border-radius: 24rpx;
  overflow: hidden;
  margin: 24rpx 0;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.06);
  border: 1rpx solid #F1F5F9;
}

.card-header {
  padding: 24rpx 32rpx;
  background: #F8FAFC;
  border-bottom: 1rpx solid #E2E8F0;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.card-icon { font-size: 32rpx; }
.card-title { 
  font-size: 30rpx; 
  font-weight: 600; 
  color: #1E293B; 
  letter-spacing: 1rpx;
}

.price-swiper {
  height: 220rpx;
  margin: 30rpx 0;
}

.swiper-item-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  overflow: visible;
}

.price-card-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  /* Transparent background for text-only look */
  background: transparent;
  width: 100%;
  height: 100%;
  transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}

.active-card {
  transform: scale(1.15);
  opacity: 1;
  /* Subtle text shadow or emphasize instead of box shadow */
  text-shadow: 0 4rpx 12rpx rgba(0,0,0,0.05);
  z-index: 10;
}

.inactive-card {
  transform: scale(0.85);
  opacity: 0.5;
  filter: grayscale(0.8);
}

.price-tag {
  font-size: 20rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-weight: 500;
  margin-bottom: 8rpx;
}

.tag-green { color: #059669; background: #D1FAE5; }
.tag-blue { color: #2563EB; background: #DBEAFE; }
.tag-orange { color: #D97706; background: #FEF3C7; }

.price-val-row {
  display: flex;
  align-items: baseline;
  justify-content: center;
  margin: 8rpx 0;
}

.currency {
  font-size: 24rpx;
  margin-right: 2rpx;
  font-weight: 600;
}

.amount {
  font-size: 40rpx; /* base size */
  font-weight: 800;
  font-family: 'Roboto', sans-serif;
}

.amount-input {
  font-size: 48rpx;
  font-weight: 800;
  font-family: 'Roboto', sans-serif;
  width: 200rpx;
  text-align: center;
  border-bottom: 2rpx solid #E2E8F0;
  height: 60rpx;
  line-height: 60rpx;
}

.text-green { color: #059669; }
.text-blue { color: #2563EB; }
.text-orange { color: #D97706; }

.active-card .amount { font-size: 48rpx; } /* larger when active */

.price-desc {
  font-size: 20rpx;
  color: #94A3B8;
}

.card-footer {
  padding: 0 32rpx 32rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.action-btn {
  height: 88rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.3s ease, box-shadow 0.3s ease; /* Smooth transition */
  position: relative;
  overflow: hidden;
  
  &:active { transform: scale(0.97); }
  
  /* Fixed gradient overlay for interaction depth */
  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.15), rgba(0,0,0,0.05));
    pointer-events: none;
  }
}

.btn-green {
  background-color: #059669;
  box-shadow: 0 4rpx 16rpx rgba(5, 150, 105, 0.25);
}

.btn-blue {
  background-color: $uni-color-primary;
  box-shadow: 0 4rpx 16rpx rgba(26, 75, 156, 0.25);
}

.btn-orange {
  background-color: #D97706;
  box-shadow: 0 4rpx 16rpx rgba(217, 119, 6, 0.25);
}

.btn-text {
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
}

.action-row-secondary {
  display: flex;
  gap: 16rpx;
}

.btn-outline {
  flex: 1;
  border: 1rpx solid #CBD5E1;
  background: #fff;
}

.btn-text-outline {
  color: #475569;
  font-size: 28rpx;
}

.btn-ghost {
  flex: 1;
  background: #F1F5F9;
}

.btn-text-ghost {
  color: #64748B;
  font-size: 28rpx;
}
</style>
