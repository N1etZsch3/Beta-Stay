<template>
  <view class="price-card">
    <text class="card-title">定价建议</text>
    <view class="price-tiers">
      <view class="tier">
        <text class="tier-label">保守价</text>
        <text class="tier-price conservative">¥{{ pricing.conservative_price }}</text>
      </view>
      <view class="tier tier-main">
        <text class="tier-label">建议价</text>
        <text class="tier-price suggested">¥{{ pricing.suggested_price }}</text>
      </view>
      <view class="tier">
        <text class="tier-label">激进价</text>
        <text class="tier-price aggressive">¥{{ pricing.aggressive_price }}</text>
      </view>
    </view>
    <view class="card-actions">
      <button size="mini" @click="$emit('adopt', pricing.suggested_price)">采纳建议价</button>
      <button size="mini" @click="$emit('reject')">不合适</button>
      <button size="mini" @click="$emit('adjust')">手动调整</button>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  pricing: {
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }
}>()
defineEmits<{ adopt: [price: number]; reject: []; adjust: [] }>()
</script>

<style scoped>
.price-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.08);
  margin: 16rpx 0;
}
.card-title {
  font-size: 28rpx;
  font-weight: bold;
  margin-bottom: 20rpx;
}
.price-tiers {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20rpx;
}
.tier { text-align: center; }
.tier-label { font-size: 24rpx; color: #999; display: block; }
.tier-price { font-size: 36rpx; font-weight: bold; display: block; margin-top: 8rpx; }
.conservative { color: #52c41a; }
.suggested { color: #1890ff; font-size: 44rpx; }
.aggressive { color: #ff4d4f; }
.tier-main { transform: scale(1.1); }
.card-actions {
  display: flex;
  gap: 16rpx;
  justify-content: center;
}
</style>
