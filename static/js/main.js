/* ============================================================
   马铃薯病害智能诊断系统 - 主 JavaScript
   ============================================================ */

// 侧边栏切换
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    // 点击内容区关闭侧边栏（移动端）
    const mainContent = document.querySelector('.main-content');
    if (mainContent && sidebar) {
        mainContent.addEventListener('click', function() {
            if (sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
    }
});


// 工具函数
const Utils = {
    // 格式化日期
    formatDate: function(date) {
        if (typeof date === 'string') date = new Date(date);
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${d} ${h}:${min}`;
    },

    // 获取风险等级样式类
    getRiskClass: function(level) {
        if (level.includes('高')) return 'tag-red';
        if (level.includes('中')) return 'tag-orange';
        return 'tag-green';
    },

    // 获取风险等级颜色
    getRiskColor: function(level) {
        if (level.includes('高')) return '#ef4444';
        if (level.includes('中')) return '#f59e0b';
        return '#22c55e';
    },

    // 生长期中文映射
    growthStageMap: {
        'seedling': '苗期',
        'vegetative': '生长期',
        'tuber': '块茎期',
        'harvest': '成熟期'
    },

    getGrowthStageName: function(stage) {
        return this.growthStageMap[stage] || stage;
    },

    // 病害中文映射
    diseaseNameMap: {
        'early_blight': '早疫病',
        'late_blight': '晚疫病',
        'healthy': '健康'
    },

    getDiseaseName: function(disease) {
        return this.diseaseNameMap[disease] || disease;
    },

    // 显示加载状态
    showLoading: function(element, text) {
        text = text || '加载中...';
        element.innerHTML = '<div class="loading"><div class="spinner"></div>' + text + '</div>';
    },

    // 显示空状态
    showEmpty: function(element, title, desc) {
        element.innerHTML = '<div class="empty-state">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' +
            '<div class="empty-state-title">' + title + '</div>' +
            '<div class="empty-state-desc">' + (desc || '') + '</div>' +
            '</div>';
    }
};
