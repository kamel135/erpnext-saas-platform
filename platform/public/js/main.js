// تحميل قائمة العملاء
async function loadTenants() {
    try {
        const response = await fetch('/api/tenants');
        const tenants = await response.json();
        
        const tableBody = document.getElementById('tenantsTable');
        tableBody.innerHTML = '';
        
        if (tenants.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        لا يوجد عملاء حتى الآن. قم بإضافة أول عميل!
                    </td>
                </tr>
            `;
        } else {
            tenants.forEach(tenant => {
                const statusBadge = tenant.status === 'active' 
                    ? '<span class="badge bg-success">نشط</span>'
                    : tenant.status === 'creating' 
                    ? '<span class="badge bg-warning">جاري الإنشاء</span>'
                    : '<span class="badge bg-secondary">غير نشط</span>';
                
                const row = `
                    <tr>
                        <td>${tenant.name}</td>
                        <td><code>${tenant.subdomain}</code></td>
                        <td>${tenant.email}</td>
                        <td><span class="badge bg-info">${tenant.plan}</span></td>
                        <td>${statusBadge}</td>
                        <td>${new Date(tenant.created_at).toLocaleDateString('ar-EG')}</td>
                        <td>
                            <a href="http://${tenant.subdomain}.localhost:8080" 
                               target="_blank" 
                               class="btn btn-sm btn-primary">
                                <i class="bi bi-box-arrow-up-right"></i> فتح
                            </a>
                            <button class="btn btn-sm btn-info" 
                                    onclick="viewStats(${tenant.id})">
                                <i class="bi bi-graph-up"></i> إحصائيات
                            </button>
                        </td>
                    </tr>
                `;
                tableBody.innerHTML += row;
            });
        }
        
        // تحديث الإحصائيات
        document.getElementById('totalTenants').textContent = tenants.length;
        document.getElementById('activeTenants').textContent = 
            tenants.filter(t => t.status === 'active').length;
            
    } catch (error) {
        console.error('Error loading tenants:', error);
        const tableBody = document.getElementById('tenantsTable');
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">
                    خطأ في تحميل البيانات
                </td>
            </tr>
        `;
    }
}

// إنشاء عميل جديد
document.getElementById('createTenantForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> جاري الإنشاء...';
    submitButton.disabled = true;
    
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch('/api/tenants', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            Swal.fire({
                icon: 'success',
                title: 'تم بنجاح!',
                text: 'تم إنشاء العميل بنجاح. سيستغرق التشغيل بضع دقائق.',
                confirmButtonText: 'حسناً'
            });
            e.target.reset();
            loadTenants();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'خطأ!',
                text: result.error || 'حدث خطأ في إنشاء العميل',
                confirmButtonText: 'حسناً'
            });
        }
    } catch (error) {
        console.error('Error creating tenant:', error);
        Swal.fire({
            icon: 'error',
            title: 'خطأ!',
            text: 'حدث خطأ في الاتصال بالخادم',
            confirmButtonText: 'حسناً'
        });
    } finally {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
});

// عرض إحصائيات العميل
async function viewStats(tenantId) {
    try {
        const response = await fetch(`/api/tenants/${tenantId}/resources`);
        const stats = await response.json();
        
        const modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <h6>استخدام المعالج (CPU)</h6>
                    <div class="progress">
                        <div class="progress-bar" style="width: ${stats.cpu || 0}%">
                            ${stats.cpu || 0}%
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>استخدام الذاكرة</h6>
                    <div class="progress">
                        <div class="progress-bar bg-info" style="width: ${stats.memory?.percent || 0}%">
                            ${stats.memory?.percent || 0}%
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('statsContent').innerHTML = modalContent;
        const modal = new bootstrap.Modal(document.getElementById('statsModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading stats:', error);
        Swal.fire({
            icon: 'error',
            title: 'خطأ!',
            text: 'لا يمكن تحميل الإحصائيات',
            confirmButtonText: 'حسناً'
        });
    }
}

// تحميل البيانات عند فتح الصفحة
window.onload = () => {
    loadTenants();
    // تحديث كل 30 ثانية
    setInterval(loadTenants, 30000);
};
