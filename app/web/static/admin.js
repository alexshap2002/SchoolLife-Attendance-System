// School of Life - Admin Interface JavaScript
// Простий та функціональний CRUD
// Version: 2025-09-09-15:00 - Fixed API endpoints

// API клієнт
const API_BASE = window.location.origin + '/api';
let isPopulatingSelects = false;

// Глобальні змінні для даних
let allClubsData = [];
let allTeachersData = [];

async function apiCall(path, method = 'GET', data = null) {
    const url = `${API_BASE}/${path}`;
    const options = {
        method,
        headers: {'Content-Type': 'application/json'}
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    console.log(`🔗 API ${method} ${url}`);
    
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error');
            throw new Error(`${method} ${url} -> ${response.status}: ${errorText}`);
        }
        
        return response.status === 204 ? null : await response.json();
    } catch (error) {
        console.error('❌ API Error:', error);
        // Покращуємо повідомлення помилки для користувача
        let userMessage = 'Помилка API';
        if (error.message.includes('students')) {
            userMessage = 'Помилка завантаження даних учнів';
        } else if (error.message.includes('teachers')) {
            userMessage = 'Помилка завантаження даних вчителів';
        } else if (error.message.includes('clubs')) {
            userMessage = 'Помилка завантаження даних гуртків';
        } else if (error.message.includes('enrollments')) {
            userMessage = 'Помилка завантаження записів на гуртки';
        } else if (error.message.includes('attendance')) {
            userMessage = 'Помилка завантаження даних відвідуваності';
        }
        
        showAlert(`${userMessage}: ${error.message}`, 'danger');
        throw error;
    }
}

// Утиліти
function showAlert(message, type = 'info') {
    // Створюємо або знаходимо toast контейнер
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Створюємо toast
    const toastId = 'toast-' + Date.now();
    const toastDiv = document.createElement('div');
    toastDiv.id = toastId;
    toastDiv.className = `toast align-items-center text-bg-${type} border-0`;
    toastDiv.role = 'alert';
    toastDiv.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
        ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastDiv);
    
    // Показуємо toast
    const toast = new bootstrap.Toast(toastDiv, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Видаляємо після закриття
    toastDiv.addEventListener('hidden.bs.toast', () => {
        toastDiv.remove();
    });
}

function showLoading(show = true) {
    let spinner = document.getElementById('loadingSpinner');
    if (!spinner && show) {
        spinner = document.createElement('div');
        spinner.id = 'loadingSpinner';
        spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Завантаження...</span></div>';
        spinner.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;';
        document.body.appendChild(spinner);
    }
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}

// === СТУДЕНТИ ===
async function viewStudent(id) {
    try {
        showLoading(true);
        const student = await apiCall(`students/${id}`);
        showLoading(false);
        
        let modal = document.getElementById('viewStudentModal');
        if (!modal) {
            modal = createViewStudentModal();
        }
        
        document.getElementById('studentDetails').innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5 class="text-primary">${student.first_name} ${student.last_name}</h5>
                    <hr>
                    <p><strong>Вік:</strong> ${student.age || 'Не вказано'}</p>
                    <p><strong>Клас:</strong> ${student.grade || 'Не вказано'}</p>
                    <p><strong>Телефон:</strong> ${student.phone_child || 'Не вказано'}</p>
                </div>
                <div class="col-md-6">
                    <h6>Батьки та контакти</h6>
                    <hr>
                    <p><strong>ПІБ батьків:</strong> ${student.parent_name || 'Не вказано'}</p>
                    <p><strong>Телефон матері:</strong> ${student.phone_mother || 'Не вказано'}</p>
                    <p><strong>Телефон батька:</strong> ${student.phone_father || 'Не вказано'}</p>
                    <p><strong>Адреса:</strong> ${student.address || 'Не вказано'}</p>
                </div>
            </div>
        `;
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
    }
}

// Функція для переходу на повну сторінку учня
function viewStudentFullInfo(studentId) {
    // Переходимо на нову сторінку з повною інформацією
    window.open(`/admin/students/${studentId}/full`, '_blank');
}

// Довідка про повну інформацію
function showFullInfoHelp() {
    const content = `
        <div class="alert alert-info">
            <h5><i class="bi bi-info-circle"></i> Як переглянути повну інформацію про учня?</h5>
            <p>Для перегляду повної інформації про учня, включаючи всі деталі про батьків, пільги, та статистику відвідуваності:</p>
            <ol>
                <li>Знайдіть потрібного учня в таблиці</li>
                <li>Натисніть кнопку <span class="badge bg-info"><i class="bi bi-person-lines-fill"></i></span> в колонці "Дії"</li>
                <li>Відкриється нова сторінка з повною інформацією про учня</li>
            </ol>
            <p class="mb-0"><strong>Примітка:</strong> Сторінка відкриється в новій вкладці браузера.</p>
        </div>
    `;
    
    showModal('Повна інформація про учнів', content, '', 'Зрозуміло');
}

async function editStudent(id) {
    try {
        showLoading(true);
        const student = await apiCall(`students/${id}`);
        showLoading(false);
        
        // Основні поля
        document.getElementById('editStudentId').value = id;
        document.getElementById('editFirstName').value = student.first_name || '';
        document.getElementById('editLastName').value = student.last_name || '';
        document.getElementById('editBirthDate').value = student.birth_date || '';
        document.getElementById('editAge').value = student.age || '';
        document.getElementById('editGrade').value = student.grade || '';
        document.getElementById('editPhoneChild').value = student.phone_child || '';
        document.getElementById('editLocation').value = student.location || '';
        document.getElementById('editAddress').value = student.address || '';
        
        // Батьки
        document.getElementById('editParentName').value = student.parent_name || '';
        document.getElementById('editFatherName').value = student.father_name || '';
        document.getElementById('editMotherName').value = student.mother_name || '';
        document.getElementById('editPhoneMother').value = student.phone_mother || '';
        document.getElementById('editPhoneFather').value = student.phone_father || '';
        
        // Додаткові поля
        document.getElementById('editSettlementType').value = student.settlement_type || '';
        document.getElementById('editBenefitOther').value = student.benefit_other || '';
        
        // Пільги (checkboxes)
        document.getElementById('editBenefitLowIncome').checked = student.benefit_low_income || false;
        document.getElementById('editBenefitLargeFamily').checked = student.benefit_large_family || false;
        document.getElementById('editBenefitMilitaryFamily').checked = student.benefit_military_family || false;
        document.getElementById('editBenefitInternallyDisplaced').checked = student.benefit_internally_displaced || false;
        document.getElementById('editBenefitOrphan').checked = student.benefit_orphan || false;
        document.getElementById('editBenefitDisability').checked = student.benefit_disability || false;
        document.getElementById('editBenefitSocialRisk').checked = student.benefit_social_risk || false;
        
        new bootstrap.Modal(document.getElementById('editStudentModal')).show();
    } catch (error) {
        showLoading(false);
    }
}

async function deleteStudent(id) {
    if (!confirm('Ви впевнені, що хочете видалити цього учня?')) {
        return;
    }
    
    try {
        showLoading(true);
        await apiCall(`students/${id}`, 'DELETE');
        showLoading(false);
        showAlert('Учня успішно видалено', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

async function saveStudent() {
    const form = document.getElementById('addStudentForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    
    // Збираємо дату народження
    let birth_date = null;
    const birthDateValue = formData.get('birthDate');
    if (birthDateValue) {
        birth_date = birthDateValue;
    }
    
    const studentData = {
        first_name: formData.get('firstName')?.trim(),
        last_name: formData.get('lastName')?.trim(),
        birth_date: birth_date,
        age: formData.get('age') ? parseInt(formData.get('age')) : null,
        grade: formData.get('grade')?.trim() || null,
        phone_child: formData.get('phoneChild')?.trim() || null,
        location: formData.get('location')?.trim() || null,
        address: formData.get('address')?.trim() || null,
        parent_name: formData.get('parentName')?.trim() || null,
        father_name: formData.get('fatherName')?.trim() || null,
        mother_name: formData.get('motherName')?.trim() || null,
        phone_mother: formData.get('phoneMother')?.trim() || null,
        phone_father: formData.get('phoneFather')?.trim() || null,
        settlement_type: formData.get('settlementType')?.trim() || null,
        benefit_other: formData.get('benefitOther')?.trim() || null,
        
        // Пільги (checkbox fields)
        benefit_low_income: formData.get('benefitLowIncome') ? true : false,
        benefit_large_family: formData.get('benefitLargeFamily') ? true : false,
        benefit_military_family: formData.get('benefitMilitaryFamily') ? true : false,
        benefit_internally_displaced: formData.get('benefitInternallyDisplaced') ? true : false,
        benefit_orphan: formData.get('benefitOrphan') ? true : false,
        benefit_disability: formData.get('benefitDisability') ? true : false,
        benefit_social_risk: formData.get('benefitSocialRisk') ? true : false,
    };
    
    if (!studentData.first_name || !studentData.last_name) {
        showAlert('Ім\'я та прізвище обов\'язкові!', 'warning');
        return;
    }
    
    // DEBUG: Логуємо дані що відправляємо
    console.log('📤 Відправка даних учня:', studentData);
    console.log('📅 Дата народження:', studentData.birth_date, typeof studentData.birth_date);
    
    try {
        showLoading(true);
        await apiCall('students', 'POST', studentData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('addStudentModal')).hide();
        showAlert('Учня успішно додано', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

async function updateStudent() {
    const form = document.getElementById('editStudentForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const id = document.getElementById('editStudentId').value;
    const firstName = document.getElementById('editFirstName').value?.trim();
    const lastName = document.getElementById('editLastName').value?.trim();
    
    if (!firstName || !lastName) {
        showAlert('Ім\'я та прізвище обов\'язкові!', 'warning');
        return;
    }
    
    // Збираємо дату народження
    let birth_date = null;
    const birthDateValue = document.getElementById('editBirthDate').value;
    if (birthDateValue) {
        birth_date = birthDateValue;
    }
    
    const studentData = {
        first_name: firstName,
        last_name: lastName,
        birth_date: birth_date,
        age: document.getElementById('editAge').value ? parseInt(document.getElementById('editAge').value) : null,
        grade: document.getElementById('editGrade').value?.trim() || null,
        phone_child: document.getElementById('editPhoneChild').value?.trim() || null,
        location: document.getElementById('editLocation').value?.trim() || null,
        address: document.getElementById('editAddress').value?.trim() || null,
        parent_name: document.getElementById('editParentName').value?.trim() || null,
        father_name: document.getElementById('editFatherName').value?.trim() || null,
        mother_name: document.getElementById('editMotherName').value?.trim() || null,
        phone_mother: document.getElementById('editPhoneMother').value?.trim() || null,
        phone_father: document.getElementById('editPhoneFather').value?.trim() || null,
        settlement_type: document.getElementById('editSettlementType').value?.trim() || null,
        benefit_other: document.getElementById('editBenefitOther').value?.trim() || null,
        
        // Пільги (checkbox fields)
        benefit_low_income: document.getElementById('editBenefitLowIncome').checked,
        benefit_large_family: document.getElementById('editBenefitLargeFamily').checked,
        benefit_military_family: document.getElementById('editBenefitMilitaryFamily').checked,
        benefit_internally_displaced: document.getElementById('editBenefitInternallyDisplaced').checked,
        benefit_orphan: document.getElementById('editBenefitOrphan').checked,
        benefit_disability: document.getElementById('editBenefitDisability').checked,
        benefit_social_risk: document.getElementById('editBenefitSocialRisk').checked,
    };
    
    try {
        showLoading(true);
        const result = await apiCall(`students/${id}`, 'PUT', studentData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('editStudentModal')).hide();
        showAlert(`Учня "${result.first_name} ${result.last_name}" успішно оновлено`, 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

// === ВЧИТЕЛІ ===
async function viewTeacher(id) {
    try {
        showLoading(true);
        const teacher = await apiCall(`teachers/${id}`);
        showLoading(false);
        
        let modal = document.getElementById('viewTeacherModal');
        if (!modal) {
            modal = createViewTeacherModal();
        }
        
        document.getElementById('teacherDetails').innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5 class="text-primary">${teacher.full_name}</h5>
                    <hr>
                    <p><strong>Статус:</strong> ${teacher.active ? '<span class="badge bg-success">Активний</span>' : '<span class="badge bg-secondary">Неактивний</span>'}</p>
                    <p><strong>Дата створення:</strong> ${new Date(teacher.created_at).toLocaleDateString('uk-UA')}</p>
                </div>
                <div class="col-md-6">
                    <h6>Telegram</h6>
                    <hr>
                    <p><strong>Username:</strong> ${teacher.tg_username ? '@' + teacher.tg_username : 'Не вказано'}</p>
                    <p><strong>Chat ID:</strong> ${teacher.tg_chat_id || 'Не підключений'}</p>
                    <p><strong>Статус боту:</strong> ${teacher.tg_chat_id ? '<span class="badge bg-success">Підключений</span>' : '<span class="badge bg-warning">Не підключений</span>'}</p>
                </div>
            </div>
        `;
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
    }
}

async function editTeacher(id) {
    try {
        showLoading(true);
        const teacher = await apiCall(`teachers/${id}`);
        showLoading(false);
        
        document.getElementById('editTeacherId').value = id;
        document.getElementById('editFullName').value = teacher.full_name;
        document.getElementById('editTgUsername').value = teacher.tg_username || '';
        document.getElementById('editTgChatId').value = teacher.tg_chat_id || '';
        document.getElementById('editActive').checked = teacher.active;
        
        new bootstrap.Modal(document.getElementById('editTeacherModal')).show();
    } catch (error) {
        showLoading(false);
    }
}

async function saveTeacher() {
    const form = document.getElementById('addTeacherForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    const teacherData = {
        full_name: formData.get('fullName')?.trim(),
        tg_username: formData.get('tgUsername')?.trim() || null,
        tg_chat_id: formData.get('tgChatId') ? parseInt(formData.get('tgChatId')) : null,
        active: formData.get('active') === 'on',
    };
    
    if (!teacherData.full_name) {
        showAlert('Повне ім\'я обов\'язкове!', 'warning');
        return;
    }
    
    try {
        showLoading(true);
        await apiCall('teachers', 'POST', teacherData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('addTeacherModal')).hide();
        showAlert('Вчителя успішно додано', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

async function updateTeacher() {
    const id = document.getElementById('editTeacherId').value;
    const fullName = document.getElementById('editFullName').value?.trim();
    
    if (!fullName) {
        showAlert('Повне ім\'я обов\'язкове!', 'warning');
        return;
    }
    
    const teacherData = {
        full_name: fullName,
        tg_username: document.getElementById('editTgUsername').value?.trim() || null,
        tg_chat_id: document.getElementById('editTgChatId').value ? parseInt(document.getElementById('editTgChatId').value) : null,
        active: document.getElementById('editActive').checked,
    };
    
    try {
        showLoading(true);
        const result = await apiCall(`teachers/${id}`, 'PUT', teacherData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('editTeacherModal')).hide();
        showAlert(`Вчителя "${result.full_name}" успішно оновлено`, 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

async function deleteTeacher(id) {
    try {
        showLoading(true);
        
        // Спочатку отримуємо інформацію про залежності
        const dependencies = await apiCall(`teachers/${id}/dependencies`, 'GET');
        showLoading(false);
        
        // Показуємо модальне вікно з деталями
        showDeleteTeacherModal(dependencies);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка перевірки залежностей:', error);
        showAlert(`Помилка перевірки залежностей: ${error.message}`, 'danger');
    }
}

// Показати модальне вікно видалення вчителя
function showDeleteTeacherModal(dependencies) {
    const modalId = 'deleteTeacherModal';
    
    // Видаляємо попереднє модальне вікно якщо існує
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Створюємо модальне вікно
    const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header ${dependencies.can_delete_safely ? 'bg-info' : 'bg-warning'}">
                        <h5 class="modal-title text-white">
                            <i class="bi bi-exclamation-triangle"></i>
                            ${dependencies.can_delete_safely ? 'Підтвердження видалення' : 'Попередження про видалення'}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6 class="mb-3">Вчитель: <strong class="text-primary">${dependencies.teacher_name}</strong></h6>
                                
                                ${dependencies.can_delete_safely ? 
                                    `<div class="alert alert-success">
                                        <i class="bi bi-check-circle"></i>
                                        <strong>Безпечне видалення</strong><br>
                                        У цього вчителя немає історичних даних (зарплати, проведених уроків).
                                    </div>` :
                                    `<div class="alert alert-warning">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        <strong>Розумне видалення</strong><br>
                                        Вчитель буде видалений, але історичні дані збережуться для звітності.
                                    </div>`
                                }
                                
                                ${!dependencies.can_delete_safely ? generateTeacherDependenciesDetails(dependencies) : ''}
                            </div>
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-header">
                                        <h6 class="mb-0"><i class="bi bi-info-circle"></i> Статистика</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row text-center g-2">
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-primary mb-0">${dependencies.dependencies.schedules}</h5>
                                                    <small>Розкладів</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-info mb-0">${dependencies.dependencies.conducted_lessons}</h5>
                                                    <small>Проведених уроків</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-success mb-0">${dependencies.dependencies.attendance_records}</h5>
                                                    <small>Відвідувань</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-warning mb-0">${dependencies.dependencies.payroll_records}</h5>
                                                    <small>Зарплат</small>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${dependencies.has_historical_data ? 
                            `<div class="mt-3 p-3 bg-light rounded">
                                <h6><i class="bi bi-shield-check"></i> Що буде збережено:</h6>
                                <ul class="mb-0">
                                    ${dependencies.dependencies.conducted_lessons > 0 ? `<li>📚 Проведені уроки (${dependencies.dependencies.conducted_lessons}) - для звітності</li>` : ''}
                                    ${dependencies.dependencies.attendance_records > 0 ? `<li>✅ Записи відвідуваності (${dependencies.dependencies.attendance_records}) - для історії</li>` : ''}
                                    ${dependencies.dependencies.payroll_records > 0 ? `<li>💰 Нарахована зарплата (${dependencies.dependencies.payroll_records}) - для бухгалтерії</li>` : ''}
                                </ul>
                                <div class="mt-2 alert alert-info">
                                    <i class="bi bi-info-circle"></i>
                                    <strong>Механізм збереження:</strong> 
                                    Історичні дані будуть збережені під ім'ям <strong>"[ВИДАЛЕНО] ${dependencies.teacher_name}"</strong>
                                </div>
                            </div>` : ''
                        }
                        
                        ${!dependencies.can_delete_safely ? 
                            `<div class="mt-3 p-3 bg-danger bg-opacity-10 rounded">
                                <h6><i class="bi bi-trash"></i> Що буде видалено:</h6>
                                <ul class="mb-0">
                                    ${dependencies.dependencies.schedules > 0 ? `<li>📅 Поточні розклади (${dependencies.dependencies.schedules}) - стануть неактивними</li>` : ''}
                                    ${dependencies.dependencies.pay_rates > 0 ? `<li>💸 Ставки оплати (${dependencies.dependencies.pay_rates}) - налаштування</li>` : ''}
                                    <li>🤖 Автоматичні нагадування в Telegram</li>
                                    <li>📝 Майбутні уроки без відвідуваності</li>
                                </ul>
                            </div>` : ''
                        }
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x-circle"></i> Скасувати
                        </button>
                        <button type="button" class="btn ${dependencies.can_delete_safely ? 'btn-primary' : 'btn-danger'}" 
                                onclick="confirmDeleteTeacher('${dependencies.teacher_id}', ${dependencies.can_delete_safely})">
                            <i class="bi bi-trash"></i> 
                            ${dependencies.can_delete_safely ? 'Видалити' : 'Видалити зі збереженням історії'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
`;
    
    // Додаємо до body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Показуємо модальне вікно
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

// Генерація деталей залежностей для вчителя
function generateTeacherDependenciesDetails(dependencies) {
    return `
        <div class="mt-3">
            <h6><i class="bi bi-list-check"></i> Детальний аналіз залежностей:</h6>
            <div class="row g-2">
                ${dependencies.dependencies.schedules > 0 ? 
                    `<div class="col-12">
                        <div class="alert alert-primary py-2">
                            <i class="bi bi-calendar"></i>
                            <strong>${dependencies.dependencies.schedules} розкладів</strong> - стануть неактивними
                            <br><small class="text-muted">Залишаться для зв'язку з історичними уроками</small>
                        </div>
                    </div>` : ''
                }
                ${dependencies.dependencies.lesson_events > 0 ? 
                    `<div class="col-12">
                        <div class="alert alert-info py-2">
                            <i class="bi bi-journal"></i>
                            <strong>${dependencies.dependencies.lesson_events} уроків</strong> 
                            (${dependencies.dependencies.lesson_events_with_attendance} з відвідуваністю)
                            <br><small class="text-muted">Майбутні уроки видаляться, проведені - зберігаються</small>
                        </div>
                    </div>` : ''
                }
                ${dependencies.dependencies.pay_rates > 0 ? 
                    `<div class="col-12">
                        <div class="alert alert-warning py-2">
                            <i class="bi bi-currency-dollar"></i>
                            <strong>${dependencies.dependencies.pay_rates} ставок оплати</strong> - будуть видалені
                            <br><small class="text-muted">Це налаштування, не історичні дані</small>
                        </div>
                    </div>` : ''
                }
            </div>
        </div>
    `;
}

// Підтвердження видалення вчителя
async function confirmDeleteTeacher(teacherId, canDeleteSafely) {
    try {
        // Закриваємо модальне вікно
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteTeacherModal'));
        modal.hide();
        
        // Виконуємо видалення
        showLoading(true);
        const deleteParams = canDeleteSafely ? '' : '?force=true';
        const result = await apiCall(`teachers/${teacherId}${deleteParams}`, 'DELETE');
        showLoading(false);
        
        // Показуємо результат
        const teacherName = document.querySelector('#deleteTeacherModal .text-primary').textContent;
        const actionText = result.action === 'smart_deleted' ? 'розумно видалено з збереженням історії' :
                          result.action === 'deactivated' ? 'деактивовано' : 'видалено';
        
        showAlert(`Вчитель "${teacherName}" ${actionText}`, 'success');
        setTimeout(() => location.reload(), 1500);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка видалення вчителя:', error);
        showAlert(`Помилка видалення вчителя: ${error.message}`, 'danger');
    }
}

// === ГУРТКИ ===
async function viewClub(id) {
    try {
        showLoading(true);
        
        // Завантажуємо дані гуртка та додаткову статистику паралельно
        const [club, schedules, students] = await Promise.all([
            apiCall(`clubs/${id}`),
            apiCall(`schedules?club_id=${id}`).catch(() => []),
            apiCall(`students?club_id=${id}`).catch(() => [])
        ]);
        
        showLoading(false);
        
        let modal = document.getElementById('viewClubModal');
        if (!modal) {
            modal = createViewClubModal();
        }
        
        // Рахуємо статистику
        const activeSchedules = schedules.filter(s => s.active).length;
        const totalStudents = students.length;
        
        document.getElementById('clubDetails').innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5 class="text-primary">
                        <i class="bi bi-collection"></i> ${club.name}
                    </h5>
                    <hr>
                    <p><strong>Тривалість:</strong> 
                        <span class="badge bg-info">${club.duration_min} хв</span>
                    </p>
                    <p><strong>Локація:</strong> 
                        <i class="bi bi-geo-alt"></i> ${club.location}
                    </p>
                    <p><strong>Дата створення:</strong> 
                        ${new Date(club.created_at).toLocaleDateString('uk-UA')}
                    </p>
                </div>
                <div class="col-md-6">
                    <h6><i class="bi bi-graph-up"></i> Статистика</h6>
                    <hr>
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="card bg-light">
                                <div class="card-body p-2">
                                    <h4 class="text-primary">${activeSchedules}</h4>
                                    <small class="text-muted">Активних розкладів</small>
                </div>
            </div>
                        </div>
                        <div class="col-6">
                            <div class="card bg-light">
                                <div class="card-body p-2">
                                    <h4 class="text-success">${totalStudents}</h4>
                                    <small class="text-muted">Записаних учнів</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <p><strong>ID гуртка:</strong> <code>#${club.id}</code></p>
                    </div>
                </div>
            </div>
            
            ${schedules.length > 0 ? `
            <hr>
            <h6><i class="bi bi-calendar-week"></i> Розклади</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>День тижня</th>
                            <th>Час</th>
                            <th>Вчитель</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${schedules.map(schedule => {
                            const weekdays = {
                                0: "Понеділок", 1: "Вівторок", 2: "Середа", 3: "Четвер",
                                4: "П'ятниця", 5: "Субота", 6: "Неділя"
                            };
                            return `
                                <tr>
                                    <td>${weekdays[schedule.weekday] || 'Невідомо'}</td>
                                    <td><strong>${schedule.start_time}</strong></td>
                                    <td>${schedule.teacher ? schedule.teacher.full_name : 'Не призначено'}</td>
                                    <td>
                                        <span class="badge ${schedule.active ? 'bg-success' : 'bg-secondary'}">
                                            ${schedule.active ? 'Активний' : 'Неактивний'}
                                        </span>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
            ` : '<hr><p class="text-muted text-center"><i class="bi bi-calendar-x"></i> Розкладів для цього гуртка ще немає</p>'}
        `;
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
        console.error('Помилка перегляду гуртка:', error);
        showAlert(`Помилка завантаження деталей гуртка: ${error.message}`, 'danger');
    }
}

async function editClub(id) {
    try {
        showLoading(true);
        const club = await apiCall(`clubs/${id}`);
        showLoading(false);
        
        let modal = document.getElementById('editClubModal');
        if (!modal) {
            modal = createEditClubModal();
        }
        
        // Заповнюємо форму даними
        document.getElementById('editClubId').value = id;
        document.getElementById('editClubName').value = club.name;
        document.getElementById('editClubDuration').value = club.duration_min;
        document.getElementById('editClubLocation').value = club.location;
        
        // Додаємо інформацію про гурток в заголовок
        const modalTitle = modal.querySelector('.modal-title');
        modalTitle.innerHTML = `
            <i class="bi bi-pencil"></i> Редагувати гурток 
            <small class="text-muted">#${club.id}</small>
        `;
        
        // Додаємо валідацію в реальному часі
        const inputs = modal.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                if (input.checkValidity()) {
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                } else {
                    input.classList.remove('is-valid');
                    input.classList.add('is-invalid');
                }
            });
        });
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
        console.error('Помилка редагування гуртка:', error);
        showAlert(`Помилка завантаження гуртка для редагування: ${error.message}`, 'danger');
    }
}

async function saveClub() {
    console.log('🚀 saveClub function called');
    
    const form = document.getElementById('addClubForm');
    if (!form.checkValidity()) {
        console.log('❌ Form validation failed');
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    const clubData = {
        name: formData.get('clubName')?.trim(),
        duration_min: parseInt(formData.get('duration')),
        location: formData.get('location')?.trim(),
    };
    
    console.log('📋 Club data to send:', clubData);
    
    if (!clubData.name || !clubData.location) {
        console.log('❌ Missing required fields');
        showAlert('Назва та локація обов\'язкові!', 'warning');
        return;
    }
    
    try {
        console.log('📡 Sending API request...');
        showLoading(true);
        const result = await apiCall('clubs', 'POST', clubData);
        console.log('✅ API request successful:', result);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('addClubModal')).hide();
        showAlert('Гурток успішно додано', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        console.error('💥 API request failed:', error);
        showLoading(false);
    }
}

async function updateClub() {
    const id = document.getElementById('editClubId').value;
    const nameInput = document.getElementById('editClubName');
    const durationInput = document.getElementById('editClubDuration');
    const locationInput = document.getElementById('editClubLocation');
    
    const name = nameInput.value?.trim();
    const duration = parseInt(durationInput.value);
    const location = locationInput.value?.trim();
    
    // Валідація з виділенням помилкових полів
    let hasErrors = false;
    
    if (!name) {
        nameInput.classList.add('is-invalid');
        hasErrors = true;
    }
    
    if (!location) {
        locationInput.classList.add('is-invalid');
        hasErrors = true;
    }
    
    if (duration < 30 || duration > 180) {
        durationInput.classList.add('is-invalid');
        hasErrors = true;
    }
    
    if (hasErrors) {
        showAlert('❌ Заповніть всі обов\'язкові поля коректно!', 'warning');
        return;
    }
    
    const clubData = {
        name: name,
        duration_min: duration,
        location: location,
    };
    
    try {
        showLoading(true);
        console.log(`📝 Оновлюємо гурток ID=${id}:`, clubData);
        
        const result = await apiCall(`clubs/${id}`, 'PUT', clubData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('editClubModal')).hide();
        
        // Показуємо детальне повідомлення про зміни
        showAlert(`
            ✅ <strong>Гурток успішно оновлено!</strong><br>
            📝 <strong>Назва:</strong> ${result.name}<br>
            ⏱️ <strong>Тривалість:</strong> ${result.duration_min} хв<br>
            📍 <strong>Локація:</strong> ${result.location}
        `, 'success');
        
        // Оновлюємо сторінку з затримкою
        setTimeout(() => {
            console.log('🔄 Оновлюємо сторінку після успішного редагування...');
            location.reload();
        }, 2000);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка оновлення гуртка:', error);
        showAlert(`❌ Помилка оновлення гуртка: ${error.message}`, 'danger');
    }
}

async function deleteClub(id) {
    try {
        showLoading(true);
        
        // Спочатку отримуємо інформацію про залежності
        const dependencies = await apiCall(`clubs/${id}/dependencies`, 'GET');
        showLoading(false);
        
        // Показуємо модальне вікно з деталями
        showDeleteClubModal(dependencies);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка перевірки залежностей:', error);
        showAlert(`Помилка перевірки залежностей: ${error.message}`, 'danger');
    }
}

// Показати модальне вікно видалення гуртка
function showDeleteClubModal(dependencies) {
    const modalId = 'deleteClubModal';
    
    // Видаляємо попереднє модальне вікно якщо існує
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Створюємо модальне вікно
    const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header ${dependencies.can_delete_safely ? 'bg-info' : 'bg-warning'}">
                        <h5 class="modal-title text-white">
                            <i class="bi bi-exclamation-triangle"></i>
                            ${dependencies.can_delete_safely ? 'Підтвердження видалення' : 'Попередження про видалення'}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6 class="mb-3">Гурток: <strong class="text-primary">${dependencies.club_name}</strong></h6>
                                
                                ${dependencies.can_delete_safely ? 
                                    `<div class="alert alert-success">
                                        <i class="bi bi-check-circle"></i>
                                        <strong>Безпечне видалення</strong><br>
                                        У цього гуртка немає прив'язаних учнів або розкладів.
                                    </div>` :
                                    `<div class="alert alert-warning">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        <strong>Каскадне видалення</strong><br>
                                        Видалення цього гуртка вплине на інші дані в системі.
                                    </div>`
                                }
                                
                                ${!dependencies.can_delete_safely ? generateDependenciesDetails(dependencies) : ''}
                            </div>
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-header">
                                        <h6 class="mb-0"><i class="bi bi-info-circle"></i> Статистика</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row text-center g-2">
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-primary mb-0">${dependencies.dependencies.enrolled_students}</h5>
                                                    <small>Учнів</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-info mb-0">${dependencies.dependencies.schedules}</h5>
                                                    <small>Розкладів</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-success mb-0">${dependencies.dependencies.conducted_lessons}</h5>
                                                    <small>Уроків</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="border rounded p-2">
                                                    <h5 class="text-warning mb-0">${dependencies.dependencies.attendance_records}</h5>
                                                    <small>Відвідувань</small>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${!dependencies.can_delete_safely ? 
                            `<div class="mt-3 p-3 bg-light rounded">
                                <h6><i class="bi bi-shield-check"></i> Що буде збережено:</h6>
                                <ul class="mb-0">
                                    <li>📚 Всі проведені уроки (${dependencies.dependencies.conducted_lessons}) - для звітності</li>
                                    <li>✅ Записи відвідуваності (${dependencies.dependencies.attendance_records}) - для історії</li>
                                    <li>💰 Нарахована зарплата - для бухгалтерії</li>
                                </ul>
                            </div>` : ''
                        }
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x-circle"></i> Скасувати
                        </button>
                        <button type="button" class="btn ${dependencies.can_delete_safely ? 'btn-primary' : 'btn-danger'}" 
                                onclick="confirmDeleteClub('${dependencies.club_id}', ${dependencies.can_delete_safely})">
                            <i class="bi bi-trash"></i> 
                            ${dependencies.can_delete_safely ? 'Видалити' : 'Видалити з усіма залежностями'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Додаємо до body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Показуємо модальне вікно
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

// Генерація деталей залежностей
function generateDependenciesDetails(dependencies) {
    return `
        <div class="mt-3">
            <h6><i class="bi bi-exclamation-diamond"></i> Що буде видалено:</h6>
            <div class="row g-3">
                ${dependencies.dependencies.enrolled_students > 0 ? 
                    `<div class="col-12">
                        <div class="alert alert-warning py-2">
                            <i class="bi bi-people"></i>
                            <strong>${dependencies.dependencies.enrolled_students} учнів</strong> будуть відписані від гуртка
                            <br><small class="text-muted">Учні зможуть записатися на інші гуртки</small>
                            <div class="mt-2">
                                <button type="button" class="btn btn-sm btn-outline-secondary" 
                                        onclick="toggleStudentsList('${dependencies.club_id}')">
                                    <i class="bi bi-list-ul"></i> Показати список учнів
                                </button>
                                <div id="studentsList_${dependencies.club_id}" class="mt-2" style="display: none;">
                                    <div class="text-center">
                                        <div class="spinner-border spinner-border-sm" role="status"></div>
                                        <span class="ms-2">Завантажуємо список...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>` : ''
                }
                ${dependencies.dependencies.schedules > 0 ? 
                    `<div class="col-12">
                        <div class="alert alert-info py-2">
                            <i class="bi bi-calendar"></i>
                            <strong>${dependencies.dependencies.schedules} розкладів</strong> будуть видалені
                            <br><small class="text-muted">Включаючи всі заплановані уроки</small>
                            <div class="mt-2">
                                <button type="button" class="btn btn-sm btn-outline-secondary" 
                                        onclick="toggleSchedulesList('${dependencies.club_id}')">
                                    <i class="bi bi-calendar3"></i> Показати розклади
                                </button>
                                <div id="schedulesList_${dependencies.club_id}" class="mt-2" style="display: none;">
                                    <div class="text-center">
                                        <div class="spinner-border spinner-border-sm" role="status"></div>
                                        <span class="ms-2">Завантажуємо розклади...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>` : ''
                }
            </div>
        </div>
    `;
}

// Показати/сховати список учнів
async function toggleStudentsList(clubId) {
    const container = document.getElementById(`studentsList_${clubId}`);
    const button = container.previousElementSibling;
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        button.innerHTML = '<i class="bi bi-chevron-up"></i> Сховати список учнів';
        
        // Завантажуємо детальну інформацію
        try {
            const details = await apiCall(`clubs/${clubId}/dependencies?include_students=true`, 'GET');
            
            if (details.details && details.details.students.length > 0) {
                const studentsHtml = details.details.students.map(student => 
                    `<div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                        <span><i class="bi bi-person"></i> ${student.full_name}</span>
                        <small class="text-muted">${student.grade ? `${student.grade} клас` : ''} ${student.age ? `(${student.age} р.)` : ''}</small>
                    </div>`
                ).join('');
                
                container.innerHTML = `
                    <div class="bg-light p-2 rounded">
                        <h6 class="mb-2 text-primary">Учні які будуть відписані:</h6>
                        ${studentsHtml}
                    </div>
                `;
            } else {
                container.innerHTML = '<div class="text-muted">Немає учнів для відображення</div>';
            }
        } catch (error) {
            container.innerHTML = '<div class="text-danger">Помилка завантаження списку учнів</div>';
        }
    } else {
        container.style.display = 'none';
        button.innerHTML = '<i class="bi bi-list-ul"></i> Показати список учнів';
    }
}

// Показати/сховати список розкладів
async function toggleSchedulesList(clubId) {
    const container = document.getElementById(`schedulesList_${clubId}`);
    const button = container.previousElementSibling;
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        button.innerHTML = '<i class="bi bi-chevron-up"></i> Сховати розклади';
        
        // Завантажуємо детальну інформацію
        try {
            const details = await apiCall(`clubs/${clubId}/dependencies?include_students=true`, 'GET');
            
            if (details.details && details.details.schedules.length > 0) {
                const schedulesHtml = details.details.schedules.map(schedule => 
                    `<div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                        <span><i class="bi bi-calendar-event"></i> ${schedule.display}</span>
                        <small class="text-muted">ID: ${schedule.id}</small>
                    </div>`
                ).join('');
                
                container.innerHTML = `
                    <div class="bg-light p-2 rounded">
                        <h6 class="mb-2 text-info">Розклади які будуть видалені:</h6>
                        ${schedulesHtml}
                    </div>
                `;
            } else {
                container.innerHTML = '<div class="text-muted">Немає розкладів для відображення</div>';
            }
        } catch (error) {
            container.innerHTML = '<div class="text-danger">Помилка завантаження списку розкладів</div>';
        }
    } else {
        container.style.display = 'none';
        button.innerHTML = '<i class="bi bi-calendar3"></i> Показати розклади';
    }
}

// Підтвердження видалення гуртка
async function confirmDeleteClub(clubId, canDeleteSafely) {
    try {
        // Закриваємо модальне вікно
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteClubModal'));
        modal.hide();
        
        // Виконуємо видалення
        showLoading(true);
        const deleteParams = canDeleteSafely ? '' : '?force=true';
        await apiCall(`clubs/${clubId}${deleteParams}`, 'DELETE');
        showLoading(false);
        
        const clubName = document.querySelector('#deleteClubModal .text-primary').textContent;
        showAlert(`Гурток "${clubName}" успішно видалено`, 'success');
        setTimeout(() => location.reload(), 1500);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка видалення гуртка:', error);
        showAlert(`Помилка видалення гуртка: ${error.message}`, 'danger');
    }
}

// Створення модальних вікон для перегляду
function createViewStudentModal() {
    const modalHTML = `
        <div class="modal fade" id="viewStudentModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Деталі учня</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="studentDetails">
                        <!-- Деталі завантажуються тут -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрити</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('viewStudentModal');
}

function createViewTeacherModal() {
    const modalHTML = `
        <div class="modal fade" id="viewTeacherModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Деталі вчителя</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="teacherDetails">
                        <!-- Деталі завантажуються тут -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрити</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('viewTeacherModal');
}

function createViewClubModal() {
    const modalHTML = `
        <div class="modal fade" id="viewClubModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Деталі гуртка</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="clubDetails">
                        <!-- Деталі завантажуються тут -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрити</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('viewClubModal');
}

function createEditClubModal() {
    const modalHTML = `
        <div class="modal fade" id="editClubModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Редагувати гурток</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editClubForm">
                            <input type="hidden" id="editClubId">
                            <div class="mb-3">
                                <label for="editClubName" class="form-label">Назва гуртка *</label>
                                <input type="text" class="form-control" id="editClubName" required>
                            </div>
                            <div class="mb-3">
                                <label for="editClubDuration" class="form-label">Тривалість (хвилини) *</label>
                                <input type="number" class="form-control" id="editClubDuration" min="30" max="180" required>
                            </div>
                            <div class="mb-3">
                                <label for="editClubLocation" class="form-label">Локація *</label>
                                <input type="text" class="form-control" id="editClubLocation" required>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Скасувати</button>
                        <button type="button" class="btn btn-primary" onclick="updateClub()">Зберегти зміни</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('editClubModal');
}

// === РОЗКЛАД ===
async function viewSchedule(id) {
    try {
        showLoading(true);
        const schedule = await apiCall(`schedules/${id}`);
        showLoading(false);
        
        let modal = document.getElementById('viewScheduleModal');
        if (!modal) {
            modal = createViewScheduleModal();
        }
        
        const weekdays = {1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 5: "П'ятниця"};
        
        document.getElementById('scheduleDetails').innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5 class="text-primary">${schedule.club?.name || 'Невідомий гурток'}</h5>
                    <hr>
                    <p><strong>День тижня:</strong> <span class="badge bg-primary">${weekdays[schedule.weekday]}</span></p>
                    <p><strong>Час:</strong> ${schedule.start_time}</p>
                    <p><strong>Статус:</strong> ${schedule.active ? '<span class="badge bg-success">Активний</span>' : '<span class="badge bg-secondary">Неактивний</span>'}</p>
                </div>
                <div class="col-md-6">
                    <h6>Деталі</h6>
                    <hr>
                    <p><strong>Вчитель:</strong> ${schedule.teacher?.full_name || 'Не призначено'}</p>
                    <p><strong>Тривалість:</strong> ${schedule.club?.duration_min || 60} хвилин</p>
                    <p><strong>Локація:</strong> ${schedule.club?.location || 'Не вказано'}</p>
                </div>
            </div>
        `;
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
    }
}

async function editSchedule(id) {
    try {
        showLoading(true);
        const [schedule, clubs, teachers] = await Promise.all([
            apiCall(`schedules/${id}`),
            apiCall('clubs'),
            apiCall('teachers')
        ]);
        showLoading(false);
        
        let modal = document.getElementById('editScheduleModal');
        if (!modal) {
            modal = createEditScheduleModal();
        }
        
        // Заповнити випадаючі списки
        fillSelectOptions('editScheduleClub', clubs, 'id', 'name');
        fillSelectOptions('editScheduleTeacher', teachers, 'id', 'full_name');
        
        // Заповнити форму
        document.getElementById('editScheduleId').value = id;
        document.getElementById('editScheduleClub').value = schedule.club_id;
        document.getElementById('editScheduleTeacher').value = schedule.teacher_id;
        document.getElementById('editScheduleWeekday').value = schedule.weekday;
        document.getElementById('editScheduleTime').value = schedule.start_time;
        document.getElementById('editScheduleActive').checked = schedule.active;
        
        new bootstrap.Modal(modal).show();
    } catch (error) {
        showLoading(false);
    }
}

async function saveSchedule() {
    console.log('🚀 saveSchedule function called');
    
    if (isPopulatingSelects) {
        console.warn('⚠️ Still populating selects, aborting save');
        return;
    }
    
    const form = document.getElementById('addScheduleForm');
    if (!form.checkValidity()) {
        console.log('❌ Form validation failed');
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    
    // Логування всіх значень з форми
    console.log('📋 Raw form data:');
    for (let [key, value] of formData.entries()) {
        console.log(`  ${key}: "${value}"`);
    }
    
    const clubId = formData.get('clubId');
    const teacherId = formData.get('teacherId');
    const weekday = Number(formData.get('weekday'));
    const startTime = formData.get('startTime');
    const active = form.querySelector('#scheduleActive')?.checked ?? false;
    
    if (!clubId || !teacherId) {
        showAlert('Оберіть гурток і вчителя', 'warning');
        return;
    }
    
    const payload = {
        club_id: Number(clubId),
        teacher_id: Number(teacherId),
        weekday,
        start_time: startTime,
        group_name: 'Група 1',
        active
    };
    
    console.log('📊 Processed schedule data:', payload);
    
    if (isNaN(payload.weekday) || payload.weekday < 1 || payload.weekday > 5) {
        console.log('❌ Validation failed - invalid weekday');
        showAlert('Оберіть день тижня!', 'warning');
        return;
    }
    
    if (!payload.start_time) {
        console.log('❌ Validation failed - missing start_time');
        showAlert('Вкажіть час початку!', 'warning');
        return;
    }
    
    try {
        console.log('📡 Sending API request...');
        showLoading(true);
        const result = await apiCall('schedules', 'POST', payload);
        console.log('✅ Schedule created successfully:', result);
        showLoading(false);
        
        // Очищуємо форму
        form.reset();
        
        bootstrap.Modal.getInstance(document.getElementById('addScheduleModal')).hide();
        showAlert('Заняття успішно додано', 'success');
        
        // Перезавантажуємо сторінку щоб показати новий розклад
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    } catch (error) {
        console.error('💥 API request failed:', error);
        showLoading(false);
    }
}

async function updateSchedule() {
    const id = document.getElementById('editScheduleId').value;
    const clubId = document.getElementById('editScheduleClub').value;
    const teacherId = document.getElementById('editScheduleTeacher').value;
    const weekday = document.getElementById('editScheduleWeekday').value;
    
    if (!clubId || !teacherId || !weekday) {
        showAlert('Всі поля обов\'язкові!', 'warning');
        return;
    }
    
    const scheduleData = {
        club_id: parseInt(clubId),
        teacher_id: parseInt(teacherId),
        weekday: parseInt(weekday),
        start_time: document.getElementById('editScheduleTime').value,
        active: document.getElementById('editScheduleActive').checked,
    };
    
    try {
        showLoading(true);
        await apiCall(`schedules/${id}`, 'PUT', scheduleData);
        showLoading(false);
        
        bootstrap.Modal.getInstance(document.getElementById('editScheduleModal')).hide();
        showAlert('Заняття успішно оновлено', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

async function deleteSchedule(id) {
    if (!confirm('Ви впевнені, що хочете видалити це заняття?')) {
        return;
    }
    
    try {
        showLoading(true);
        await apiCall(`schedules/${id}`, 'DELETE');
        showLoading(false);
        showAlert('Заняття успішно видалено', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showLoading(false);
    }
}

// Функція для відкриття модального вікна додавання розкладу
async function openAddScheduleModal() {
    console.log('🚀 Opening add schedule modal...');
    try {
        showLoading(true);
        await loadScheduleSelects();     // тільки тут
        showLoading(false);
        const modal = new bootstrap.Modal(document.getElementById('addScheduleModal'));
        modal.show();
    } catch (e) {
        showLoading(false);
        showAlert('Помилка при завантаженні даних', 'danger');
    }
}

// Допоміжні функції для розкладу
async function loadScheduleSelects() {
    isPopulatingSelects = true;
    try {
        console.log('📥 Loading schedule select options...');
        const [clubs, teachers] = await Promise.all([
            apiCall('clubs'),
            apiCall('teachers')
        ]);
        
        console.log('📊 Loaded data:');
        console.log(`  Clubs: ${clubs.length} items`, clubs);
        console.log(`  Teachers: ${teachers.length} items`, teachers);
        
        fillSelectOptions('scheduleClub', clubs, 'id', 'name');
        fillSelectOptions('scheduleTeacher', teachers, 'id', 'full_name');
        
        console.log('✅ Select options filled successfully');
    } catch (error) {
        console.error('❌ Error loading select options:', error);
    } finally {
        isPopulatingSelects = false;
    }
}

function fillSelectOptions(selectId, items, valueField, textField) {
    console.log(`🔄 Filling select #${selectId} with ${items.length} items`);
    
    const select = document.getElementById(selectId);
    if (!select) {
        console.error(`❌ Select element #${selectId} not found`);
        return;
    }
    
    if (!Array.isArray(items)) {
        console.error(`❌ Items is not an array:`, items);
        return;
    }
    
    // Зберігаємо попередній вибір користувача
    const prevValue = select.value;
    
    // Очищуємо select
    select.innerHTML = '';
    
    // Створюємо placeholder
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.disabled = true;
    placeholder.selected = !prevValue; // selected лише якщо ще не було вибору
    placeholder.textContent = selectId.includes('Club') ? 'Оберіть гурток' : 'Оберіть вчителя';
    select.appendChild(placeholder);
    
    // Додаємо опції
    for (const item of items) {
        if (!item || typeof item !== 'object') {
            console.warn(`⚠️ Invalid item:`, item);
            continue;
        }
        
        const option = document.createElement('option');
        option.value = String(item[valueField]); // Явно до рядка
        option.textContent = item[textField];
        select.appendChild(option);
    }
        
    // Відновлюємо попередній вибір якщо він досі існує
    if (prevValue && [...select.options].some(o => o.value === prevValue)) {
        select.value = prevValue;
        }
    
    console.log(`✅ Select #${selectId} filled with ${items.length} options (prev value: ${prevValue}, current: ${select.value})`);
}

function createViewScheduleModal() {
    const modalHTML = `
        <div class="modal fade" id="viewScheduleModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Деталі заняття</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="scheduleDetails">
                        <!-- Деталі завантажуються тут -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрити</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('viewScheduleModal');
}

function createEditScheduleModal() {
    const modalHTML = `
        <div class="modal fade" id="editScheduleModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Редагувати заняття</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editScheduleForm">
                            <input type="hidden" id="editScheduleId">
                            <div class="mb-3">
                                <label for="editScheduleClub" class="form-label">Гурток *</label>
                                <select class="form-select" id="editScheduleClub" required>
                                    <option value="">Оберіть гурток</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="editScheduleTeacher" class="form-label">Вчитель *</label>
                                <select class="form-select" id="editScheduleTeacher" required>
                                    <option value="">Оберіть вчителя</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="editScheduleWeekday" class="form-label">День тижня *</label>
                                <select class="form-select" id="editScheduleWeekday" required>
                                    <option value="">Оберіть день</option>
                                    <option value="1">Понеділок</option>
                                    <option value="2">Вівторок</option>
                                    <option value="3">Середа</option>
                                    <option value="4">Четвер</option>
                                    <option value="5">П'ятниця</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="editScheduleTime" class="form-label">Час початку *</label>
                                <input type="time" class="form-control" id="editScheduleTime" required>
                            </div>
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="editScheduleActive">
                                    <label class="form-check-label" for="editScheduleActive">
                                        Активне заняття
                                    </label>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Скасувати</button>
                        <button type="button" class="btn btn-primary" onclick="updateSchedule()">Зберегти зміни</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('editScheduleModal');
}


// Ініціалізація
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ School of Life Admin Interface loaded');
    console.log('🔗 API Base:', API_BASE);
    
    // Завантажити списки для розкладу, якщо ми на сторінці розкладу
    if (window.location.pathname.includes('/schedules')) {
        loadScheduleSelects();
    }
    
    // Завантажити дані учнів, якщо ми на сторінці учнів
    if (window.location.pathname.includes('/students')) {
        loadStudentsData();
    }
    
    // Завантажити дані вчителів, якщо ми на сторінці вчителів
    if (window.location.pathname.includes('/teachers')) {
        loadTeachersData();
    }
    
    // Завантажити дані розкладу, якщо ми на сторінці розкладу
    if (window.location.pathname.includes('/schedules')) {
        // 🔥 ПЕРЕВІРЯЄМО чи є новий виправлений код
        if (!window.scheduleFixApplied) {
            loadSchedulesTableData();
        } else {
            console.log('🔧 [ADMIN.JS] Пропускаю loadSchedulesTableData() - використовується новий код з фільтрами');
        }
    }
    
    // Завантажити дані гуртків, якщо ми на сторінці гуртків
    if (window.location.pathname.includes('/clubs')) {
        loadClubsData();
    }
    
    // Завантажити дані боту, якщо ми на сторінці боту
    if (window.location.pathname.includes('/bot')) {
        loadBotData();
    }
});

// === РОЗШИРЕНА ТАБЛИЦЯ УЧНІВ ===

let allStudentsData = [];
// allClubsData - використовуємо глобальну змінну
let isLoadingStudentsData = false; // Захист від багаторазових викликів

// Завантаження всіх даних для таблиці учнів
async function loadStudentsData() {
    // Захист від багаторазових викликів
    if (isLoadingStudentsData) {
        console.log('⏳ Дані учнів вже завантажуються, пропускаємо дублювання');
        return;
    }
    
    isLoadingStudentsData = true;
    try {
        showLoading(true);
        console.log('📥 Завантаження даних учнів...');
        
        // Завантажуємо паралельно всі потрібні дані
        const [students, clubs, enrollments] = await Promise.all([
            apiCall('students'),
            apiCall('clubs'),
            apiCall('enrollments')
        ]);
        
        allStudentsData = students;
        allClubsData = clubs;
        
        console.log(`📊 Завантажено: ${students.length} учнів, ${clubs.length} гуртків, ${enrollments.length} записів`);
        
        // Прив'язуємо записи до учнів
        allStudentsData.forEach(student => {
            student.enrolledClubs = enrollments
                .filter(e => e.student_id === student.id)
                .map(e => e.club_id);
        });
        
        buildStudentsTable();
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка завантаження даних учнів:', error);
        // Помилка вже показана в apiCall, не дублюємо
    } finally {
        isLoadingStudentsData = false; // Очищаємо флаг
    }
}

// Побудова заголовків таблиці з розширеними фільтрами
function buildStudentsTable() {
    const tableHead = document.getElementById('studentsTableHead');
    const tableBody = document.getElementById('studentsTableBody');
    
    // ПЕРШИЙ РЯДОК - НАЗВИ КОЛОНОК
    let headerHTML = `
        <tr>
            <th class="text-center">Ім'я</th>
            <th class="text-center">Прізвище</th>
            <th class="text-center">День народження</th>
            <th class="text-center">Вік</th>
            <th class="text-center">Клас</th>
            <th class="text-center">Телефон дитини</th>
            <th class="text-center">ПІБ матері</th>
            <th class="text-center">Телефон матері</th>
            <th class="text-center">ПІБ батька</th>
            <th class="text-center">Телефон батька</th>`;
    
    // Додаємо назви гуртків
    allClubsData.forEach(club => {
        headerHTML += `<th class="text-center" title="Записаний на ${club.name}?">${club.name}</th>`;
    });
    
    headerHTML += `<th class="text-center">Дії</th></tr>`;
    
    // ДРУГИЙ РЯДОК - ПРОСТІ ФІЛЬТРИ
    headerHTML += `
        <tr class="filter-row">
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterStudentFirstName" 
                       placeholder="Фільтр по імені" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterStudentLastName" 
                       placeholder="Фільтр по прізвищу" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="date" class="form-control form-control-sm filter-input" id="filterBirthDate" 
                       onchange="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterStudentAge" 
                       placeholder="Фільтр по віку" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterStudentGrade" 
                       placeholder="Фільтр по класу" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterChildPhone" 
                       placeholder="Телефон дитини" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterMotherName" 
                       placeholder="ПІБ матері" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterMotherPhone" 
                       placeholder="Тел. матері" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterFatherName" 
                       placeholder="ПІБ батька" onkeyup="filterStudents()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterFatherPhone" 
                       placeholder="Тел. батька" onkeyup="filterStudents()">
            </td>`;
    
    // Додаємо фільтри для гуртків
    allClubsData.forEach(club => {
        headerHTML += `
            <td class="text-center">
                <select class="form-select form-select-sm filter-select" id="filterClub${club.id}" onchange="filterStudents()">
                    <option value="">Всі</option>
                    <option value="enrolled">✅ Так</option>
                    <option value="not-enrolled">❌ Ні</option>
                </select>
            </td>`;
    });
    
    headerHTML += `<td></td></tr>`;
    
    tableHead.innerHTML = headerHTML;
    
    // Наповнюємо дані
    displayStudentsData(allStudentsData);
    
    // Ініціалізуємо sticky scrollbar
    setTimeout(initStickyScrollbar, 100);
}

// Відображення даних учнів
function displayStudentsData(students) {
    const tableBody = document.getElementById('studentsTableBody');
    
    if (students.length === 0) {
        const clubsCount = allClubsData.length;
        tableBody.innerHTML = `
            <tr>
                <td colspan="${7 + clubsCount}" class="text-center text-muted">
                    <i class="bi bi-people"></i><br>
                    Учнів не знайдено за заданими критеріями
                </td>
            </tr>`;
            return;
        }
        
    let bodyHTML = '';
    students.forEach(student => {
        // ВИПРАВЛЕННЯ: Правильне форматування дати
        let birthDate = '-';
        if (student.birth_date && student.birth_date !== null && student.birth_date !== '') {
            try {
                // Якщо дата у форматі YYYY-MM-DD (з API)
                if (typeof student.birth_date === 'string' && student.birth_date.includes('-')) {
                    const [year, month, day] = student.birth_date.split('-');
                    // Створюємо дату БЕЗ timezone проблем
                    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
                    birthDate = date.toLocaleDateString('uk-UA', { year: 'numeric', month: '2-digit', day: '2-digit' });
                } else {
                    // Інший формат - пробуємо стандартний парсинг
                    const date = new Date(student.birth_date);
                    if (!isNaN(date.getTime())) {
                        birthDate = date.toLocaleDateString('uk-UA', { year: 'numeric', month: '2-digit', day: '2-digit' });
                    }
                }
            } catch (e) {
                console.error('Помилка парсингу дати:', student.birth_date, e);
                birthDate = '-';
            }
        }
        
        // ВИПРАВЛЕННЯ: Показуємо ПІБ батьків (не телефон!)
        // Фільтруємо порожні/фейкові значення: null, '', '---', '—', тощо
        const isValidParentName = (name) => {
            if (!name || name === null || name === '') return false;
            const trimmed = name.trim();
            if (trimmed === '' || trimmed === '-' || trimmed === '—' || trimmed === '---' || trimmed === 'Не вказано') return false;
            return true;
        };
        
        let parentInfo = '-';
        if (isValidParentName(student.mother_name)) {
            parentInfo = student.mother_name.trim();
        } else if (isValidParentName(student.father_name)) {
            parentInfo = student.father_name.trim();
        } else if (isValidParentName(student.parent_name)) {
            parentInfo = student.parent_name.trim();
        }
        
        // Для sticky стовпців додаємо title для довгих імен
        const firstNameTitle = student.first_name.length > 12 ? `title="${student.first_name}"` : '';
        const lastNameTitle = student.last_name.length > 15 ? `title="${student.last_name}"` : '';
        
        // Фільтруємо порожні/фейкові телефони теж
        const isValidPhone = (phone) => {
            if (!phone || phone === null || phone === '') return false;
            const trimmed = phone.trim();
            if (trimmed === '' || trimmed === '-' || trimmed === '—' || trimmed === '---') return false;
            return true;
        };
        
        const childPhone = isValidPhone(student.phone_child) ? student.phone_child : '-';
        const motherNameDisplay = isValidParentName(student.mother_name) ? student.mother_name.trim() : '-';
        const motherPhoneDisplay = isValidPhone(student.phone_mother) ? student.phone_mother : '-';
        const fatherNameDisplay = isValidParentName(student.father_name) ? student.father_name.trim() : '-';
        const fatherPhoneDisplay = isValidPhone(student.phone_father) ? student.phone_father : '-';
        
        bodyHTML += `
            <tr>
                <td ${firstNameTitle}>${student.first_name}</td>
                <td ${lastNameTitle}>${student.last_name}</td>
                <td>${birthDate}</td>
                <td>${student.age || '-'}</td>
                <td>${student.grade || '-'}</td>
                <td>${childPhone}</td>
                <td>${motherNameDisplay}</td>
                <td>${motherPhoneDisplay}</td>
                <td>${fatherNameDisplay}</td>
                <td>${fatherPhoneDisplay}</td>`;
        
        // Додаємо статуси по гуртках (тільки візуальні індикатори)
        allClubsData.forEach(club => {
            const isEnrolled = student.enrolledClubs && student.enrolledClubs.includes(club.id);
            if (isEnrolled) {
                // Учень записаний - показуємо ✅ (без інтерактивності)
                bodyHTML += `
                    <td class="text-center club-status" data-student-id="${student.id}" data-club-id="${club.id}">
                        <span class="fs-5 text-success" title="Записаний на гурток '${club.name}'">✅</span>
                    </td>`;
            } else {
                // Учень не записаний - показуємо ❌ (без інтерактивності)
                bodyHTML += `
                    <td class="text-center club-status" data-student-id="${student.id}" data-club-id="${club.id}">
                        <span class="fs-5 text-muted" title="Не записаний на гурток '${club.name}'">❌</span>
                    </td>`;
            }
        });
        
        bodyHTML += `
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="viewStudent(${student.id})" title="Переглянути">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-info" 
                                onclick="viewStudentFullInfo(${student.id})" title="Повна інформація">
                            <i class="bi bi-person-lines-fill"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="editStudent(${student.id})" title="Редагувати">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="deleteStudent(${student.id})" title="Видалити">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
    });
    
    tableBody.innerHTML = bodyHTML;
    
    // Ініціалізуємо sticky scrollbar після відображення даних
    initStickyScrollbar();
}

// STICKY SCROLLBAR - Плаваючий горизонтальний скролбар (універсальна функція)
function initStickyScrollbar(containerId = 'studentsTableContainer') {
    const tableContainer = document.getElementById(containerId);
    const stickyScrollbar = document.getElementById('stickyScrollbar');
    const stickyScrollbarTrack = document.getElementById('stickyScrollbarTrack');
    const stickyScrollbarThumb = document.getElementById('stickyScrollbarThumb');
    
    if (!tableContainer || !stickyScrollbar || !stickyScrollbarTrack || !stickyScrollbarThumb) {
        return;
    }
    
    let isDragging = false;
    let startX = 0;
    let startScrollLeft = 0;
    
    // Функція для оновлення позиції та розміру thumb
    function updateStickyScrollbar() {
        const scrollWidth = tableContainer.scrollWidth;
        const clientWidth = tableContainer.clientWidth;
        const scrollLeft = tableContainer.scrollLeft;
        
        // Показуємо тільки якщо є горизонтальний скрол
        if (scrollWidth > clientWidth) {
            // Обчислюємо розмір thumb (пропорційно видимій частині)
            const thumbWidth = (clientWidth / scrollWidth) * 300; // 300px - ширина треку
            const thumbPosition = (scrollLeft / (scrollWidth - clientWidth)) * (300 - thumbWidth);
            
            stickyScrollbarThumb.style.width = thumbWidth + 'px';
            stickyScrollbarThumb.style.left = thumbPosition + 'px';
            
            // Показуємо sticky scrollbar якщо:
            // 1. Таблиця прокручена вниз (основний scrollbar не видно)
            // 2. Є горизонтальний скрол
            const tableRect = tableContainer.getBoundingClientRect();
            const scrollbarRect = tableContainer.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // Scrollbar з'являється якщо нижня частина таблиці поза екраном
            const isScrollbarHidden = scrollbarRect.bottom > windowHeight - 50;
            const hasHorizontalScroll = scrollWidth > clientWidth;
            
            if (isScrollbarHidden && hasHorizontalScroll) {
                stickyScrollbar.classList.add('visible');
            } else {
                stickyScrollbar.classList.remove('visible');
            }
        } else {
            stickyScrollbar.classList.remove('visible');
        }
    }
    
    // Обробник прокручування основної таблиці
    tableContainer.addEventListener('scroll', updateStickyScrollbar);
    
    // Обробник прокручування сторінки
    window.addEventListener('scroll', updateStickyScrollbar);
    
    // Обробник зміни розміру вікна
    window.addEventListener('resize', updateStickyScrollbar);
    
    // Обробники для drag and drop на sticky scrollbar
    stickyScrollbarThumb.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startScrollLeft = tableContainer.scrollLeft;
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - startX;
        const scrollWidth = tableContainer.scrollWidth;
        const clientWidth = tableContainer.clientWidth;
        const maxScrollLeft = scrollWidth - clientWidth;
        
        // Конвертуємо рух миші в прокрутку таблиці
        const scrollRatio = maxScrollLeft / (300 - stickyScrollbarThumb.offsetWidth);
        const newScrollLeft = startScrollLeft + (deltaX * scrollRatio);
        
        tableContainer.scrollLeft = Math.max(0, Math.min(maxScrollLeft, newScrollLeft));
    });
    
    document.addEventListener('mouseup', () => {
        isDragging = false;
        document.body.style.userSelect = '';
    });
    
    // Touch підтримка для мобільних пристроїв
    stickyScrollbarThumb.addEventListener('touchstart', (e) => {
        isDragging = true;
        startX = e.touches[0].clientX;
        startScrollLeft = tableContainer.scrollLeft;
        e.preventDefault();
    });
    
    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.touches[0].clientX - startX;
        const scrollWidth = tableContainer.scrollWidth;
        const clientWidth = tableContainer.clientWidth;
        const maxScrollLeft = scrollWidth - clientWidth;
        
        const scrollRatio = maxScrollLeft / (300 - stickyScrollbarThumb.offsetWidth);
        const newScrollLeft = startScrollLeft + (deltaX * scrollRatio);
        
        tableContainer.scrollLeft = Math.max(0, Math.min(maxScrollLeft, newScrollLeft));
        e.preventDefault();
    });
    
    document.addEventListener('touchend', () => {
        isDragging = false;
    });
    
    // Обробник кліку по треку
    stickyScrollbarTrack.addEventListener('click', (e) => {
        if (e.target === stickyScrollbarThumb) return;
        
        const rect = stickyScrollbarTrack.getBoundingClientRect();
        const clickPosition = e.clientX - rect.left;
        const scrollWidth = tableContainer.scrollWidth;
        const clientWidth = tableContainer.clientWidth;
        const maxScrollLeft = scrollWidth - clientWidth;
        
        const targetScrollLeft = (clickPosition / 300) * maxScrollLeft;
        tableContainer.scrollLeft = targetScrollLeft;
    });
    
    // Початкове оновлення
    setTimeout(updateStickyScrollbar, 100);
}


// Розширена фільтрація учнів з усіма колонками
function filterStudents() {
    console.log('🔍 Розширена фільтрація учнів...');
    
    const firstNameFilter = document.getElementById('filterStudentFirstName')?.value.toLowerCase().trim() || '';
    const lastNameFilter = document.getElementById('filterStudentLastName')?.value.toLowerCase().trim() || '';
    const birthDateFilter = document.getElementById('filterBirthDate')?.value || '';
    const ageFilter = document.getElementById('filterStudentAge')?.value || '';
    const gradeFilter = document.getElementById('filterStudentGrade')?.value.toLowerCase().trim() || '';
    
    // НОВІ ФІЛЬТРИ
    const childPhoneFilter = document.getElementById('filterChildPhone')?.value.toLowerCase().trim() || '';
    const motherNameFilter = document.getElementById('filterMotherName')?.value.toLowerCase().trim() || '';
    const motherPhoneFilter = document.getElementById('filterMotherPhone')?.value.toLowerCase().trim() || '';
    const fatherNameFilter = document.getElementById('filterFatherName')?.value.toLowerCase().trim() || '';
    const fatherPhoneFilter = document.getElementById('filterFatherPhone')?.value.toLowerCase().trim() || '';
    
    let filteredStudents = allStudentsData.filter(student => {
        // Фільтр по імені
        if (firstNameFilter && !student.first_name.toLowerCase().includes(firstNameFilter)) {
            return false;
        }
        
        // Фільтр по прізвищу
        if (lastNameFilter && !student.last_name.toLowerCase().includes(lastNameFilter)) {
            return false;
        }
        
        // Фільтр по даті народження
        if (birthDateFilter && student.birth_date !== birthDateFilter) {
            return false;
        }
        
        // Фільтр по віку (текстовий пошук)
        if (ageFilter && student.age) {
            if (!student.age.toString().includes(ageFilter)) {
                return false;
            }
        }
        
        // Фільтр по класу
        if (gradeFilter && student.grade && !student.grade.toLowerCase().includes(gradeFilter)) {
            return false;
        }
        
        // НОВІ ФІЛЬТРИ
        // Фільтр по телефону дитини
        if (childPhoneFilter && student.phone_child && !student.phone_child.toLowerCase().includes(childPhoneFilter)) {
            return false;
        }
        
        // Фільтр по ПІБ матері
        if (motherNameFilter && student.mother_name && !student.mother_name.toLowerCase().includes(motherNameFilter)) {
            return false;
        }
        
        // Фільтр по телефону матері
        if (motherPhoneFilter && student.phone_mother && !student.phone_mother.toLowerCase().includes(motherPhoneFilter)) {
            return false;
        }
        
        // Фільтр по ПІБ батька
        if (fatherNameFilter && student.father_name && !student.father_name.toLowerCase().includes(fatherNameFilter)) {
            return false;
        }
        
        // Фільтр по телефону батька
        if (fatherPhoneFilter && student.phone_father && !student.phone_father.toLowerCase().includes(fatherPhoneFilter)) {
            return false;
        }
        
        // Фільтри по гуртках
        for (const club of allClubsData) {
            const clubFilter = document.getElementById(`filterClub${club.id}`)?.value;
            if (clubFilter) {
                const isEnrolled = student.enrolledClubs && student.enrolledClubs.includes(club.id);
                if (clubFilter === 'enrolled' && !isEnrolled) {
                    return false;
                }
                if (clubFilter === 'not-enrolled' && isEnrolled) {
                    return false;
                }
            }
        }
        
        return true;
    });
    
    console.log(`📊 Показано ${filteredStudents.length} з ${allStudentsData.length} учнів`);
    displayStudentsData(filteredStudents);
}

// Видалення учня з гуртка (ВИМКНЕНО)
async function removeStudentFromClub(studentId, clubId, studentName, clubName) {
    console.log('⚠️ Функція removeStudentFromClub вимкнена. Використовуйте інші засоби для управління записами на гуртки.');
    showAlert('Функція відпису з гуртків вимкнена на цій сторінці', 'info');
        return;
    }
    
// Додавання учня до гуртка (ВИМКНЕНО)
async function addStudentToClub(studentId, clubId, studentName, clubName) {
    console.log('⚠️ Функція addStudentToClub вимкнена. Використовуйте інші засоби для управління записами на гуртки.');
    showAlert('Функція запису на гуртки вимкнена на цій сторінці', 'info');
        return;
}

// Допоміжна функція для оновлення таблиці учнів якщо вона видима
function updateStudentsTableIfVisible() {
    // Перевіряємо чи відкрита вкладка учнів
    if (window.location.pathname.includes('/students') && typeof loadStudentsData === 'function') {
        console.log('🔄 Оновлюємо таблицю учнів після змін у розкладі');
        // Невелика затримка для уникнення частих викликів
        setTimeout(() => {
        loadStudentsData();
        }, 300);
    }
}

// =============================================================================
// СЕКЦІЯ: ВЧИТЕЛІ
// =============================================================================

// allTeachersData - використовуємо глобальну змінну
let allSchedulesData = [];

// Завантаження даних вчителів з усіма зв'язками
async function loadTeachersData() {
    console.log('🔄 Завантаження даних вчителів...');
    try {
        const [teachersResponse, clubsResponse, schedulesResponse] = await Promise.all([
            apiCall('teachers', 'GET'),
            apiCall('clubs', 'GET'),
            apiCall('schedules', 'GET')
        ]);

        allTeachersData = teachersResponse;
        allClubsData = clubsResponse; // Використовуємо глобальну змінну
        allSchedulesData = schedulesResponse;

        console.log('📊 Завантажено:', {
            teachers: allTeachersData.length,
            clubs: allClubsData.length,
            schedules: allSchedulesData.length
        });

        // Обробляємо дані вчителів - додаємо інформацію про гуртки
        allTeachersData.forEach(teacher => {
            teacher.teachingClubs = allSchedulesData
                .filter(schedule => schedule.teacher_id === teacher.id && schedule.active)
                .map(schedule => schedule.club_id);
        });

        buildTeachersTable();
        
    } catch (error) {
        console.error('❌ Помилка завантаження даних вчителів:', error);
        // Помилка вже показана в apiCall, не дублюємо
    }
}

// Побудова заголовків таблиці вчителів
function buildTeachersTable() {
    const tableHead = document.getElementById('teachersTableHead');
    const tableBody = document.getElementById('teachersTableBody');
    
    if (!tableHead || !tableBody) {
        console.log('📋 Елементи таблиці вчителів не знайдені');
        return;
    }
    
    // ПЕРШИЙ РЯДОК - НАЗВИ КОЛОНОК
    let headerHTML = `
        <tr>
            <th class="text-center">Повне ім'я</th>
            <th class="text-center">Telegram</th>
            <th class="text-center">Статус</th>
            <th class="text-center">Дата створення</th>`;
    
    // Додаємо назви гуртків
    allClubsData.forEach(club => {
        headerHTML += `<th class="text-center" title="Викладає в ${club.name}?">${club.name}</th>`;
    });
    
    headerHTML += `<th class="text-center">Дії</th></tr>`;
    
    // ДРУГИЙ РЯДОК - ФІЛЬТРИ
    headerHTML += `
        <tr class="filter-row">
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterTeacherName" 
                       placeholder="Фільтр по імені" onkeyup="filterTeachers()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterTeacherTelegram" 
                       placeholder="Фільтр Telegram" onkeyup="filterTeachers()">
            </td>
            <td>
                <select class="form-select form-select-sm filter-select" id="filterTeacherStatus" onchange="filterTeachers()">
                    <option value="">Всі статуси</option>
                    <option value="active">Активний</option>
                    <option value="inactive">Неактивний</option>
                </select>
            </td>
            <td>
                <input type="date" class="form-control form-control-sm filter-input" id="filterTeacherDate" 
                       onchange="filterTeachers()">
            </td>`;
    
    // Додаємо фільтри для гуртків
    allClubsData.forEach(club => {
        headerHTML += `
            <td class="text-center">
                <select class="form-select form-select-sm filter-select" id="filterTeacherClub${club.id}" onchange="filterTeachers()">
                    <option value="">Всі</option>
                    <option value="teaching">✅ Так</option>
                    <option value="not-teaching">❌ Ні</option>
                </select>
            </td>`;
    });
    
    headerHTML += `<td></td></tr>`;
    
    tableHead.innerHTML = headerHTML;
    
    // Наповнюємо дані
    displayTeachersData(allTeachersData);
    
    // Ініціалізуємо sticky scrollbar для вчителів
    setTimeout(() => initStickyScrollbar('teachersTableContainer'), 100);
}

// Відображення даних вчителів
function displayTeachersData(teachers) {
    const tableBody = document.getElementById('teachersTableBody');
    
    if (!tableBody) {
        console.log('📋 Tbody вчителів не знайдено');
        return;
    }
    
    if (teachers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="${5 + allClubsData.length}" class="text-center text-muted">
                    <i class="bi bi-person-badge"></i><br>
                    Вчителів не знайдено за заданими критеріями
                </td>
            </tr>`;
        return;
    }
    
    let bodyHTML = '';
    
    teachers.forEach(teacher => {
        bodyHTML += `
            <tr ondblclick="editTeacher(${teacher.id})">
                <td><strong>${teacher.full_name}</strong></td>
                <td>
                    ${teacher.tg_username 
                        ? `<i class="bi bi-telegram text-info"></i> @${teacher.tg_username}
                           ${teacher.tg_chat_id ? `<br><small class="text-muted">ID: ${teacher.tg_chat_id}</small>` : ''}`
                        : '<span class="text-muted">Не підключений</span>'
                    }
                </td>
                <td>
                    <span class="badge ${teacher.active ? 'bg-success' : 'bg-secondary'}">
                        ${teacher.active ? 'Активний' : 'Неактивний'}
                    </span>
                </td>
                <td>${teacher.created_at ? new Date(teacher.created_at).toLocaleDateString('uk-UA') : '-'}</td>`;
        
        // Додаємо статуси гуртків
        allClubsData.forEach(club => {
            const isTeaching = teacher.teachingClubs && teacher.teachingClubs.includes(club.id);
            bodyHTML += `<td class="club-status">${isTeaching ? '✅' : '❌'}</td>`;
        });
        
        bodyHTML += `
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="viewTeacher(${teacher.id})" title="Переглянути">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="editTeacher(${teacher.id})" title="Редагувати">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="deleteTeacher(${teacher.id})" title="Видалити">
                            <i class="bi bi-trash"></i>
                        </button>
            </div>
                </td>
            </tr>`;
    });
    
    tableBody.innerHTML = bodyHTML;
}

// Фільтрація вчителів
function filterTeachers() {
    console.log('🔍 Фільтрація вчителів...');
    
    const nameFilter = document.getElementById('filterTeacherName')?.value.toLowerCase().trim() || '';
    const telegramFilter = document.getElementById('filterTeacherTelegram')?.value.toLowerCase().trim() || '';
    const statusFilter = document.getElementById('filterTeacherStatus')?.value || '';
    const dateFilter = document.getElementById('filterTeacherDate')?.value || '';
    
    let filteredTeachers = allTeachersData.filter(teacher => {
        // Фільтр по імені
        if (nameFilter && !teacher.full_name.toLowerCase().includes(nameFilter)) {
            return false;
        }
        
        // Фільтр по Telegram
        if (telegramFilter) {
            const telegramText = (teacher.tg_username || '').toLowerCase() + 
                                (teacher.tg_chat_id || '').toString().toLowerCase();
            if (!telegramText.includes(telegramFilter)) {
                return false;
            }
        }
        
        // Фільтр по статусу
        if (statusFilter) {
            if (statusFilter === 'active' && !teacher.active) return false;
            if (statusFilter === 'inactive' && teacher.active) return false;
        }
        
        // Фільтр по даті створення
        if (dateFilter && teacher.created_at) {
            const teacherDate = new Date(teacher.created_at).toISOString().split('T')[0];
            if (teacherDate !== dateFilter) {
                return false;
            }
        }
        
        // Фільтри по гуртках
        for (const club of allClubsData) {
            const clubFilter = document.getElementById(`filterTeacherClub${club.id}`)?.value;
            if (clubFilter) {
                const isTeaching = teacher.teachingClubs && teacher.teachingClubs.includes(club.id);
                if (clubFilter === 'teaching' && !isTeaching) {
                    return false;
                }
                if (clubFilter === 'not-teaching' && isTeaching) {
                    return false;
                }
            }
        }
        
        return true;
    });
    
    console.log(`📊 Показано ${filteredTeachers.length} з ${allTeachersData.length} вчителів`);
    displayTeachersData(filteredTeachers);
}

// =============================================================================
// СЕКЦІЯ: РОЗКЛАД
// =============================================================================

let allSchedulesTableData = [];
let currentScheduleForStudents = null;
let currentAvailableStudents = [];
let currentEnrolledStudentsData = [];

// Завантаження даних розкладу
async function loadSchedulesTableData() {
    console.log('🔄 Завантаження даних розкладу...');
    try {
        const [schedulesResponse, studentsResponse, enrollmentsResponse, clubsResponse, teachersResponse] = await Promise.all([
            apiCall('schedules', 'GET'),
            apiCall('students', 'GET'),
            apiCall('schedule-enrollments', 'GET'),
            apiCall('clubs', 'GET'),
            apiCall('teachers', 'GET')
        ]);

        allSchedulesTableData = schedulesResponse;
        allStudentsData = studentsResponse;
        
        // 🔧 FIX: Завантажуємо дані для фільтрів
        allClubsData = clubsResponse;
        allTeachersData = teachersResponse;
        
        console.log('📊 Завантажено:', {
            schedules: allSchedulesTableData.length,
            students: allStudentsData.length,
            enrollments: enrollmentsResponse.length,
            clubs: clubsResponse.length,
            teachers: teachersResponse.length
        });
        
        // Логування структури першого розкладу для діагностики
        if (allSchedulesTableData.length > 0) {
            console.log('🔍 Структура розкладу:', {
                first_schedule: allSchedulesTableData[0],
                has_club: !!allSchedulesTableData[0].club,
                has_teacher: !!allSchedulesTableData[0].teacher,
                club_name: allSchedulesTableData[0].club?.name,
                teacher_name: allSchedulesTableData[0].teacher?.full_name
            });
        }

        // Додаємо інформацію про кількість записаних учнів
        allSchedulesTableData.forEach(schedule => {
            schedule.enrolledCount = enrollmentsResponse.filter(e => e.schedule_id === schedule.id).length;
        });

        buildSchedulesTable();
        populateScheduleFilters();
        
    } catch (error) {
        console.error('❌ Помилка завантаження даних розкладу:', error);
        showAlert('Помилка завантаження даних розкладу', 'danger');
    }
}

// Заповнення фільтрів розкладу
function populateScheduleFilters() {
    console.log('🔧 Заповнення фільтрів розкладу...');
    
    // Використовуємо глобальні змінні
    const clubsData = allClubsData;
    const teachersData = allTeachersData;
    
    console.log('📋 Дані для фільтрів:', {
        clubs: clubsData?.length || 0,
        teachers: teachersData?.length || 0
    });
    
    // Заповнюємо селект гуртків
    const clubFilter = document.getElementById('filterScheduleClub');
    if (clubFilter && clubsData && clubsData.length > 0) {
        clubFilter.innerHTML = '<option value="">Всі гуртки</option>';
        clubsData.forEach(club => {
            clubFilter.innerHTML += `<option value="${club.id}">${club.name}</option>`;
        });
        console.log(`✅ Заповнено ${clubsData.length} гуртків у фільтр`);
    } else {
        console.warn('⚠️ Не вдалося заповнити фільтр гуртків:', {
            element: !!clubFilter,
            data: !!clubsData,
            length: clubsData?.length
        });
    }
    
    // Заповнюємо селект вчителів
    const teacherFilter = document.getElementById('filterScheduleTeacher');
    if (teacherFilter && teachersData && teachersData.length > 0) {
        teacherFilter.innerHTML = '<option value="">Всі вчителі</option>';
        teachersData.forEach(teacher => {
            teacherFilter.innerHTML += `<option value="${teacher.id}">${teacher.full_name}</option>`;
        });
        console.log(`✅ Заповнено ${teachersData.length} вчителів у фільтр`);
    } else {
        console.warn('⚠️ Не вдалося заповнити фільтр вчителів:', {
            element: !!teacherFilter,
            data: !!teachersData,
            length: teachersData?.length
        });
    }
}

// Фільтрація розкладу
function filterSchedules() {
    const weekdayFilter = document.getElementById('filterScheduleWeekday')?.value || '';
    const timeFilter = document.getElementById('filterScheduleTime')?.value.trim().toLowerCase() || '';
    const clubFilter = document.getElementById('filterScheduleClub')?.value || '';
    const teacherFilter = document.getElementById('filterScheduleTeacher')?.value || '';
    const durationFilter = document.getElementById('filterScheduleDuration')?.value.trim() || '';
    const studentsFilter = document.getElementById('filterScheduleStudents')?.value.trim() || '';
    const statusFilter = document.getElementById('filterScheduleStatus')?.value || '';
    
    console.log('🔍 Фільтрація розкладу:', {
        weekday: weekdayFilter,
        time: timeFilter,
        club: clubFilter,
        teacher: teacherFilter,
        duration: durationFilter,
        students: studentsFilter,
        status: statusFilter
    });
    
    const filteredSchedules = allSchedulesTableData.filter(schedule => {
        // Фільтр по дню тижня
        if (weekdayFilter && schedule.weekday.toString() !== weekdayFilter) {
            return false;
        }
        
        // Фільтр по часу
        if (timeFilter && !schedule.start_time.toLowerCase().includes(timeFilter)) {
            return false;
        }
        
        // Фільтр по гуртку
        if (clubFilter && schedule.club_id.toString() !== clubFilter) {
            return false;
        }
        
        // Фільтр по вчителю
        if (teacherFilter && schedule.teacher_id.toString() !== teacherFilter) {
            return false;
        }
        
        // Фільтр по тривалості
        if (durationFilter) {
            const duration = schedule.club ? schedule.club.duration_min || 60 : 60;
            if (!duration.toString().includes(durationFilter)) {
                return false;
            }
        }
        
        // Фільтр по кількості учнів
        if (studentsFilter) {
            const enrolledCount = schedule.enrolledCount || 0;
            if (!enrolledCount.toString().includes(studentsFilter)) {
                return false;
            }
        }
        
        // Фільтр по статусу
        if (statusFilter && schedule.active.toString() !== statusFilter) {
            return false;
        }
        
        return true;
    });
    
    console.log(`📊 Показано ${filteredSchedules.length} з ${allSchedulesTableData.length} розкладів`);
    displaySchedulesData(filteredSchedules);
}

// Побудова таблиці розкладу
function buildSchedulesTable() {
    const tableHead = document.getElementById('schedulesTableHead');
    const tableBody = document.getElementById('schedulesTableBody');
    
    if (!tableHead || !tableBody) {
        console.log('📋 Елементи таблиці розкладу не знайдені');
        return;
    }
    
    // ЗАГОЛОВКИ З ФІЛЬТРАМИ (БЕЗ КОЛОНКИ ГРУПА)
    tableHead.innerHTML = `
        <tr>
            <th class="text-center">День тижня</th>
            <th class="text-center">Час</th>
            <th class="text-center">Гурток</th>
            <th class="text-center">Вчитель</th>
            <th class="text-center">Тривалість</th>
            <th class="text-center">Учні</th>
            <th class="text-center">Статус</th>
            <th class="text-center">Дії</th>
        </tr>
        <tr class="bg-light">
            <td class="p-2">
                <select class="form-select form-select-sm" id="filterScheduleWeekday" onchange="filterSchedules()">
                    <option value="">Всі дні</option>
                    <option value="1">Понеділок</option>
                    <option value="2">Вівторок</option>
                    <option value="3">Середа</option>
                    <option value="4">Четвер</option>
                    <option value="5">П'ятниця</option>
                </select>
            </td>
            <td class="p-2">
                <input type="text" class="form-control form-control-sm" id="filterScheduleTime" 
                       placeholder="Час" onkeyup="filterSchedules()">
            </td>
            <td class="p-2">
                <select class="form-select form-select-sm" id="filterScheduleClub" onchange="filterSchedules()">
                    <option value="">Всі гуртки</option>
                </select>
            </td>
            <td class="p-2">
                <select class="form-select form-select-sm" id="filterScheduleTeacher" onchange="filterSchedules()">
                    <option value="">Всі вчителі</option>
                </select>
            </td>
            <td class="p-2">
                <input type="text" class="form-control form-control-sm" id="filterScheduleDuration" 
                       placeholder="Хв" onkeyup="filterSchedules()">
            </td>
            <td class="p-2">
                <input type="text" class="form-control form-control-sm" id="filterScheduleStudents" 
                       placeholder="К-ть" onkeyup="filterSchedules()">
            </td>
            <td class="p-2">
                <select class="form-select form-select-sm" id="filterScheduleStatus" onchange="filterSchedules()">
                    <option value="">Всі статуси</option>
                    <option value="true">Активний</option>
                    <option value="false">Неактивний</option>
                </select>
            </td>
            <td class="p-2"></td>
        </tr>`;
    
    displaySchedulesData(allSchedulesTableData);
}

// Відображення даних розкладу
function displaySchedulesData(schedules) {
    const tableBody = document.getElementById('schedulesTableBody');
    
    if (!tableBody) {
        console.log('📋 Tbody розкладу не знайдено');
        return;
    }
    
    if (schedules.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    <i class="bi bi-calendar3"></i><br>
                    Розклад ще не створено
                </td>
            </tr>`;
        return;
    }
    
    const weekdays = {
        1: "Понеділок",
        2: "Вівторок", 
        3: "Середа",
        4: "Четвер",
        5: "П'ятниця"
    };
    
    let bodyHTML = '';
    
    schedules.forEach(schedule => {
        bodyHTML += `
            <tr ondblclick="editSchedule(${schedule.id})">
                <td>
                    <span class="badge bg-primary">${weekdays[schedule.weekday] || 'Невідомо'}</span>
                </td>
                <td><strong>${schedule.start_time}</strong></td>
                <td>${schedule.club ? schedule.club.name : 'Не вказано'}</td>
                <td>${schedule.teacher ? schedule.teacher.full_name : 'Не вказано'}</td>
                <td>${schedule.club ? schedule.club.duration_min || 60 : 60} хв</td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-info" 
                            onclick="manageScheduleStudents(${schedule.id})" title="Управління учнями">
                        <i class="bi bi-people"></i> ${schedule.enrolledCount || 0}
                    </button>
                </td>
                <td>
                    <span class="badge ${schedule.active ? 'bg-success' : 'bg-secondary'}">
                        ${schedule.active ? 'Активний' : 'Неактивний'}
                    </span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="viewSchedule(${schedule.id})" title="Переглянути">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="editSchedule(${schedule.id})" title="Редагувати">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="deleteSchedule(${schedule.id})" title="Видалити">
                            <i class="bi bi-trash"></i>
                        </button>
            </div>
                </td>
            </tr>`;
    });
    
    tableBody.innerHTML = bodyHTML;
}

// Управління учнями групи
async function manageScheduleStudents(scheduleId) {
    console.log('👥 Управління учнями для розкладу:', scheduleId);
    currentScheduleForStudents = scheduleId;
    
    try {
        // Завантажуємо всіх учнів, записаних на цей розклад, гуртки та записи на гуртки
        const [allStudents, enrolledStudents, allClubs, allEnrollments] = await Promise.all([
            apiCall('students', 'GET'),
            apiCall(`schedule-enrollments/${scheduleId}`, 'GET'),
            apiCall('clubs', 'GET'),
            apiCall('enrollments', 'GET')
        ]);
        
        // Додаємо інформацію про гуртки для кожного учня
        allStudents.forEach(student => {
            const studentEnrollments = allEnrollments.filter(e => e.student_id === student.id);
            student.enrolledClubs = studentEnrollments.map(e => {
                const club = allClubs.find(c => c.id === e.club_id);
                return club ? club.name : 'Невідомий гурток';
            });
        });
        
        const enrolledStudentIds = enrolledStudents.map(e => e.student_id);
        const availableStudents = allStudents.filter(s => !enrolledStudentIds.includes(s.id));
        const enrolledStudentsWithData = allStudents.filter(s => enrolledStudentIds.includes(s.id));
        
        // Зберігаємо дані для пошуку
        currentAvailableStudents = availableStudents;
        currentEnrolledStudentsData = enrolledStudentsWithData;
        
        // Заповнюємо списки
        displayAvailableStudents(availableStudents);
        displayEnrolledStudents(enrolledStudentsWithData);
        updateStudentCounts();
        
        // Очищаємо пошукові поля
        document.getElementById('searchAvailableStudents').value = '';
        document.getElementById('searchEnrolledStudents').value = '';
        
        // Показуємо модальне вікно
        const modal = new bootstrap.Modal(document.getElementById('manageStudentsModal'));
        modal.show();
        
    } catch (error) {
        console.error('❌ Помилка завантаження учнів:', error);
        showAlert('Помилка завантаження учнів', 'danger');
    }
}

// Відображення доступних учнів з повною інформацією
function displayAvailableStudents(students) {
    const container = document.getElementById('availableStudentsList');
    
    if (students.length === 0) {
        container.innerHTML = '<p class="text-muted text-center p-4">Всі учні вже записані на цей розклад</p>';
        return;
    }
    
    let html = '';
    students.forEach(student => {
        const birthDate = student.birth_date ? new Date(student.birth_date).toLocaleDateString('uk-UA') : 'Не вказано';
        const enrolledClubs = student.enrolledClubs && student.enrolledClubs.length > 0 ? 
            student.enrolledClubs.join(', ') : 'Не записаний';
        
        html += `
            <div class="card mb-3 student-card" data-student-id="${student.id}">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="student-info flex-grow-1">
                            <h6 class="card-title mb-2">
                                <i class="bi bi-person-circle text-primary me-2"></i>
                                ${student.first_name} ${student.last_name}
                            </h6>
                            <div class="student-details small text-muted">
                                <div class="row g-2">
                                    <div class="col-6">
                                        <i class="bi bi-calendar3 me-1"></i>
                                        <strong>Вік:</strong> ${student.age || 'Не вказано'}
            </div>
                                    <div class="col-6">
                                        <i class="bi bi-book me-1"></i>
                                        <strong>Клас:</strong> ${student.grade || 'Не вказано'}
                                    </div>
                                    <div class="col-12">
                                        <i class="bi bi-gift me-1"></i>
                                        <strong>Д.н.:</strong> ${birthDate}
                                    </div>
                                    <div class="col-12">
                                        <i class="bi bi-collection me-1"></i>
                                        <strong>Гуртки:</strong> 
                                        <span class="text-info">${enrolledClubs}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-success btn-sm ms-3" 
                                onclick="enrollStudent(${student.id})" title="Додати до групи">
                            <i class="bi bi-plus-circle"></i>
                        </button>
                    </div>
                </div>
            </div>`;
    });
    
    container.innerHTML = html;
}

// Відображення записаних учнів з повною інформацією
function displayEnrolledStudents(students) {
    const container = document.getElementById('enrolledStudentsList');
    
    if (students.length === 0) {
        container.innerHTML = '<p class="text-muted text-center p-4">Учні ще не записані на цей розклад</p>';
        return;
    }
    
    let html = '';
    students.forEach(student => {
        const birthDate = student.birth_date ? new Date(student.birth_date).toLocaleDateString('uk-UA') : 'Не вказано';
        const enrolledClubs = student.enrolledClubs && student.enrolledClubs.length > 0 ? 
            student.enrolledClubs.join(', ') : 'Не записаний';
        
        html += `
            <div class="card mb-3 student-card enrolled-student" data-student-id="${student.id}">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="student-info flex-grow-1">
                            <h6 class="card-title mb-2">
                                <i class="bi bi-person-check-fill text-success me-2"></i>
                                ${student.first_name} ${student.last_name}
                            </h6>
                            <div class="student-details small text-muted">
                                <div class="row g-2">
                                    <div class="col-6">
                                        <i class="bi bi-calendar3 me-1"></i>
                                        <strong>Вік:</strong> ${student.age || 'Не вказано'}
                                    </div>
                                    <div class="col-6">
                                        <i class="bi bi-book me-1"></i>
                                        <strong>Клас:</strong> ${student.grade || 'Не вказано'}
                                    </div>
                                    <div class="col-12">
                                        <i class="bi bi-gift me-1"></i>
                                        <strong>Д.н.:</strong> ${birthDate}
                                    </div>
                                    <div class="col-12">
                                        <i class="bi bi-collection me-1"></i>
                                        <strong>Гуртки:</strong> 
                                        <span class="text-info">${enrolledClubs}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-danger btn-sm ms-3" 
                                onclick="unenrollStudentById(${student.id})" title="Видалити з групи">
                            <i class="bi bi-dash-circle"></i>
                        </button>
                    </div>
                </div>
            </div>`;
    });
    
    container.innerHTML = html;
}

// Записати учня на розклад
async function enrollStudent(studentId) {
    if (!currentScheduleForStudents) {
        showAlert('Помилка: розклад не вибрано', 'danger');
        return;
    }
    
    try {
        await apiCall('schedule-enrollments', 'POST', {
            student_id: studentId,
            schedule_id: currentScheduleForStudents
        });
        
        showAlert('Учня успішно записано', 'success');
        
        // Оновлюємо списки без повторного відкриття модального вікна
        refreshStudentLists();
        
        // Оновлюємо головну таблицю
        loadSchedulesTableData();
        
    } catch (error) {
        console.error('❌ Помилка запису учня:', error);
        showAlert('Помилка запису учня', 'danger');
    }
}

// Видалити учня з розкладу
async function unenrollStudent(enrollmentId) {
    try {
        await apiCall(`schedule-enrollments/${enrollmentId}`, 'DELETE');
        
        showAlert('Учня успішно видалено', 'success');
        
        // Оновлюємо списки без повторного відкриття модального вікна
        refreshStudentLists();
        
        // Оновлюємо головну таблицю
        loadSchedulesTableData();
        
        // Оновлюємо таблицю учнів якщо потрібно (автоматичне видалення може вплинути на записи)
        updateStudentsTableIfVisible();
        
    } catch (error) {
        console.error('❌ Помилка видалення учня:', error);
        showAlert('Помилка видалення учня', 'danger');
    }
}

// Видалити учня з розкладу за ID учня
async function unenrollStudentById(studentId) {
    try {
        await apiCall(`schedule-enrollments/student/${studentId}/schedule/${currentScheduleForStudents}`, 'DELETE');
        
        showAlert('Учня успішно видалено', 'success');
        
        // Оновлюємо списки без повторного відкриття модального вікна
        refreshStudentLists();
        
        // Оновлюємо головну таблицю
        loadSchedulesTableData();
        
        // Оновлюємо таблицю учнів якщо потрібно (автоматичне видалення може вплинути на записи)
        updateStudentsTableIfVisible();
        
    } catch (error) {
        console.error('❌ Помилка видалення учня:', error);
        showAlert('Помилка видалення учня', 'danger');
    }
}

// Пошук учнів
function searchStudents(type) {
    const searchValue = type === 'available' ? 
        document.getElementById('searchAvailableStudents').value.trim().toLowerCase() :
        document.getElementById('searchEnrolledStudents').value.trim().toLowerCase();
    
    const students = type === 'available' ? currentAvailableStudents : currentEnrolledStudentsData;
    
    if (!searchValue) {
        // Показати всіх учнів
        if (type === 'available') {
            displayAvailableStudents(students);
        } else {
            displayEnrolledStudents(students);
        }
        return;
    }
    
    // Фільтрація учнів
    const filteredStudents = students.filter(student => {
        const fullName = `${student.first_name} ${student.last_name}`.toLowerCase();
        const grade = (student.grade || '').toLowerCase();
        const age = (student.age || '').toString();
        const clubs = student.enrolledClubs ? student.enrolledClubs.join(' ').toLowerCase() : '';
        
        return fullName.includes(searchValue) ||
               grade.includes(searchValue) ||
               age.includes(searchValue) ||
               clubs.includes(searchValue);
    });
    
    // Відображення результатів
    if (type === 'available') {
        displayAvailableStudents(filteredStudents);
    } else {
        displayEnrolledStudents(filteredStudents);
    }
    
    console.log(`🔍 Знайдено ${filteredStudents.length} з ${students.length} учнів (${type})`);
}

// Оновлення лічильників учнів
function updateStudentCounts() {
    const availableCount = document.getElementById('availableCount');
    const enrolledCount = document.getElementById('enrolledCount');
    
    if (availableCount) {
        availableCount.textContent = currentAvailableStudents.length;
    }
    
    if (enrolledCount) {
        enrolledCount.textContent = currentEnrolledStudentsData.length;
    }
}

// Оновлення списків учнів без повторного відкриття модального вікна
async function refreshStudentLists() {
    if (!currentScheduleForStudents) {
        console.warn('⚠️ Розклад не вибрано для оновлення списків');
        return;
    }
    
    try {
        // Завантажуємо оновлені дані
        const [allStudents, enrolledStudents, allClubs, allEnrollments] = await Promise.all([
            apiCall('students', 'GET'),
            apiCall(`schedule-enrollments/${currentScheduleForStudents}`, 'GET'),
            apiCall('clubs', 'GET'),
            apiCall('enrollments', 'GET')
        ]);
        
        // Додаємо інформацію про гуртки для кожного учня
        allStudents.forEach(student => {
            const studentEnrollments = allEnrollments.filter(e => e.student_id === student.id);
            student.enrolledClubs = studentEnrollments.map(e => {
                const club = allClubs.find(c => c.id === e.club_id);
                return club ? club.name : 'Невідомий гурток';
            });
        });
        
        const enrolledStudentIds = enrolledStudents.map(e => e.student_id);
        const availableStudents = allStudents.filter(s => !enrolledStudentIds.includes(s.id));
        const enrolledStudentsWithData = allStudents.filter(s => enrolledStudentIds.includes(s.id));
        
        // Оновлюємо глобальні змінні
        currentAvailableStudents = availableStudents;
        currentEnrolledStudentsData = enrolledStudentsWithData;
        
        // Зберігаємо поточні значення пошуку
        const searchAvailable = document.getElementById('searchAvailableStudents')?.value || '';
        const searchEnrolled = document.getElementById('searchEnrolledStudents')?.value || '';
        
        // Відображаємо оновлені списки з урахуванням пошуку
        if (searchAvailable) {
            searchStudents('available');
        } else {
            displayAvailableStudents(availableStudents);
        }
        
        if (searchEnrolled) {
            searchStudents('enrolled');
        } else {
            displayEnrolledStudents(enrolledStudentsWithData);
        }
        
        // Оновлюємо лічильники
        updateStudentCounts();
        
        console.log('🔄 Списки учнів оновлено:', {
            available: availableStudents.length,
            enrolled: enrolledStudentsWithData.length
        });
        
    } catch (error) {
        console.error('❌ Помилка оновлення списків учнів:', error);
        showAlert('Помилка оновлення списків учнів', 'danger');
    }
}

// =============================================================================
// СЕКЦІЯ: ГУРТКИ
// =============================================================================

let allClubsTableData = [];

// Завантаження всіх даних для таблиці гуртків
async function loadClubsData() {
    try {
        showLoading(true);
        console.log('📥 Завантаження даних гуртків...');
        
        // Завантажуємо дані гуртків
        const clubs = await apiCall('clubs');
        
        allClubsTableData = clubs;
        
        console.log(`📊 Завантажено: ${clubs.length} гуртків`);
        
        buildClubsTable();
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        console.error('❌ Помилка завантаження даних гуртків:', error);
        // Помилка вже показана в apiCall, не дублюємо
    }
}

// Побудова заголовків таблиці гуртків з фільтрами
function buildClubsTable() {
    const tableHead = document.getElementById('clubsTableHead');
    const tableBody = document.getElementById('clubsTableBody');
    
    // ПЕРШИЙ РЯДОК - НАЗВИ КОЛОНОК
    let headerHTML = `
        <tr>
            <th class="text-center">Назва гуртка</th>
            <th class="text-center">Тривалість</th>
            <th class="text-center">Локація</th>
            <th class="text-center">Дата створення</th>
            <th class="text-center">Дії</th>
        </tr>`;
    
    // ДРУГИЙ РЯДОК - ФІЛЬТРИ (в стилі таблиці учнів)
    headerHTML += `
        <tr class="filter-row">
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterClubName" 
                       placeholder="Фільтр по назві" onkeyup="filterClubs()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterClubDuration" 
                       placeholder="Фільтр по тривалості" onkeyup="filterClubs()">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm filter-input" id="filterClubLocation" 
                       placeholder="Фільтр по локації" onkeyup="filterClubs()">
            </td>
            <td>
                <input type="date" class="form-control form-control-sm filter-input" id="filterClubDate" 
                       onchange="filterClubs()">
            </td>
            <td></td>
        </tr>`;
    
    tableHead.innerHTML = headerHTML;
    
    // Наповнюємо дані
    displayClubsData(allClubsTableData);
}

// Відображення даних гуртків
function displayClubsData(clubs) {
    const tableBody = document.getElementById('clubsTableBody');
    
    if (clubs.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="bi bi-collection"></i><br>
                    Гуртків не знайдено за заданими критеріями
                </td>
            </tr>`;
        return;
    }
    
    let bodyHTML = '';
    clubs.forEach(club => {
        const createdDate = club.created_at ? 
            new Date(club.created_at).toLocaleDateString('uk-UA') : '-';
        
        bodyHTML += `
            <tr ondblclick="editClub(${club.id})">
                <td><strong>${club.name}</strong></td>
                <td>
                    <span class="badge bg-info">${club.duration_min} хв</span>
                </td>
                <td>
                    <i class="bi bi-geo-alt"></i> ${club.location}
                </td>
                <td>${createdDate}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="viewClub(${club.id})" title="Переглянути">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="editClub(${club.id})" title="Редагувати">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="deleteClub(${club.id})" title="Видалити">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
    });
    
    tableBody.innerHTML = bodyHTML;
}

// Фільтрація гуртків
function filterClubs() {
    const nameFilter = document.getElementById('filterClubName').value.toLowerCase().trim();
    const durationFilter = document.getElementById('filterClubDuration').value.toLowerCase().trim();
    const locationFilter = document.getElementById('filterClubLocation').value.toLowerCase().trim();
    const dateFilter = document.getElementById('filterClubDate').value.trim();
    
    const filteredClubs = allClubsTableData.filter(club => {
        // Фільтр по назві
        const nameMatch = !nameFilter || club.name.toLowerCase().includes(nameFilter);
        
        // Фільтр по тривалості
        const durationMatch = !durationFilter || 
            club.duration_min.toString().includes(durationFilter) ||
            `${club.duration_min} хв`.toLowerCase().includes(durationFilter);
        
        // Фільтр по локації
        const locationMatch = !locationFilter || club.location.toLowerCase().includes(locationFilter);
        
        // Фільтр по даті
        let dateMatch = true;
        if (dateFilter) {
            const clubDate = new Date(club.created_at);
            const filterDate = new Date(dateFilter);
            dateMatch = clubDate.toDateString() === filterDate.toDateString();
        }
        
        return nameMatch && durationMatch && locationMatch && dateMatch;
    });
    
    console.log(`🔍 Знайдено ${filteredClubs.length} з ${allClubsTableData.length} гуртків за критеріями`);
    displayClubsData(filteredClubs);
}

// ✅ Заглушки видалено - використовуємо робочі функції на рядках 396-520

// ==================== ІМПОРТ УЧНІВ ====================

// Скачування шаблону Excel
async function downloadStudentsTemplate() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/students/template/download');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'shablon_uchniv.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showAlert('Шаблон Excel успішно скачано!', 'success');
        
    } catch (error) {
        console.error('Error downloading template:', error);
        showAlert('Помилка при скачуванні шаблону: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Імпорт учнів з Excel файлу
async function importStudents() {
    const fileInput = document.getElementById('excelFile');
    const skipDuplicates = document.getElementById('skipDuplicates').checked;
    
    if (!fileInput.files.length) {
        showAlert('Будь ласка, виберіть Excel файл для імпорту', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Перевіряємо формат файлу
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        showAlert('Будь ласка, виберіть файл Excel (.xlsx або .xls)', 'warning');
        return;
    }
    
    try {
        // Показуємо прогрес
        showImportProgress(true);
        updateImportProgress(10, 'Підготовка до імпорту...');
        
        // Створюємо FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('skip_duplicates', skipDuplicates);
        
        updateImportProgress(30, 'Завантаження файлу...');
        
        // Відправляємо запит
        const response = await fetch('/api/students/import', {
            method: 'POST',
            body: formData
        });
        
        updateImportProgress(70, 'Обробка даних...');
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Помилка при імпорті файлу');
        }
        
        const result = await response.json();
        updateImportProgress(100, 'Завершено!');
        
        // Показуємо результати
        showImportResults(result);
        
        // Оновлюємо таблицю учнів
        if (result.created_count > 0) {
            await loadStudentsData();
        }
        
    } catch (error) {
        console.error('Error importing students:', error);
        showAlert('Помилка при імпорті учнів: ' + error.message, 'danger');
        hideImportProgress();
    }
}

// Показати прогрес імпорту
function showImportProgress(show = true) {
    const progressDiv = document.getElementById('importProgress');
    const resultsDiv = document.getElementById('importResults');
    const importBtn = document.getElementById('importBtn');
    
    if (show) {
        progressDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
        importBtn.disabled = true;
        importBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Імпортуємо...';
    } else {
        progressDiv.style.display = 'none';
        importBtn.disabled = false;
        importBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> Імпортувати';
    }
}

// Оновити прогрес імпорту
function updateImportProgress(percent, status) {
    const progressBar = document.querySelector('#importProgress .progress-bar');
    const statusDiv = document.getElementById('importStatus');
    
    progressBar.style.width = percent + '%';
    progressBar.setAttribute('aria-valuenow', percent);
    statusDiv.textContent = status;
}

// Приховати прогрес
function hideImportProgress() {
    showImportProgress(false);
}

// Показати результати імпорту
function showImportResults(result) {
    const resultsDiv = document.getElementById('importResults');
    const summaryDiv = document.getElementById('importSummary');
    
    let summaryHTML = `
        <p><strong>Створено нових учнів:</strong> ${result.created_count}</p>
        <p><strong>Пропущено дублікатів:</strong> ${result.skipped_count}</p>
    `;
    
    if (result.errors && result.errors.length > 0) {
        summaryHTML += `
            <p><strong>Помилки:</strong></p>
            <ul class="mb-0">
                ${result.errors.map(error => `<li>${error}</li>`).join('')}
            </ul>
        `;
        
        // Змінюємо клас alert на warning якщо є помилки
        resultsDiv.querySelector('.alert').className = 'alert alert-warning';
    }
    
    summaryDiv.innerHTML = summaryHTML;
    resultsDiv.style.display = 'block';
    hideImportProgress();
    
    // Показуємо глобальне повідомлення
    if (result.success) {
        showAlert(result.message, result.errors.length > 0 ? 'warning' : 'success');
    }
}

// ==================== TG БОТ УПРАВЛІННЯ ====================

// Глобальні змінні для боту
let allBotSchedules = [];
let allAvailableSchedules = [];

// Завантаження даних боту
async function loadBotData() {
    try {
        showLoading(true);
        
        const [botSchedules, availableSchedules] = await Promise.all([
            apiCall('bot/schedules'),
            apiCall('bot/available-schedules')
        ]);
        
        allBotSchedules = botSchedules;
        allAvailableSchedules = availableSchedules;
        
        displayBotSchedules(allBotSchedules);
        updateBotStatistics();
        populateBotFilters();
        
    } catch (error) {
        console.error('Error loading bot data:', error);
        showAlert('Помилка завантаження даних боту: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Відображення статистики боту
function updateBotStatistics() {
    const activeCount = allBotSchedules.filter(bs => bs.enabled).length;
    const disabledCount = allBotSchedules.filter(bs => !bs.enabled).length;
    const totalSchedules = allAvailableSchedules.length;
    const withoutBotCount = allAvailableSchedules.filter(s => !s.has_bot_schedule).length;
    
    document.getElementById('activeCount').textContent = activeCount;
    document.getElementById('disabledCount').textContent = disabledCount;
    document.getElementById('totalSchedules').textContent = totalSchedules;
    document.getElementById('withoutBotCount').textContent = withoutBotCount;
}

// Заповнення фільтрів
function populateBotFilters() {
    const clubSelect = document.getElementById('filterClub');
    const teacherSelect = document.getElementById('filterTeacher');
    
    // Очищаємо фільтри
    clubSelect.innerHTML = '<option value="">Всі гуртки</option>';
    teacherSelect.innerHTML = '<option value="">Всі вчителі</option>';
    
    // Унікальні гуртки та вчителі
    const clubs = [...new Set(allBotSchedules.map(bs => bs.schedule.club_name))].sort();
    const teachers = [...new Set(allBotSchedules.map(bs => bs.schedule.teacher_name))].sort();
    
    clubs.forEach(club => {
        const option = document.createElement('option');
        option.value = club;
        option.textContent = club;
        clubSelect.appendChild(option);
    });
    
    teachers.forEach(teacher => {
        const option = document.createElement('option');
        option.value = teacher;
        option.textContent = teacher;
        teacherSelect.appendChild(option);
    });
}

// Відображення розсилок боту
function displayBotSchedules(botSchedules) {
    const tableBody = document.getElementById('botSchedulesTableBody');
    
    if (botSchedules.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="bi bi-robot"></i> Розсилки боту не знайдено
                </td>
            </tr>
        `;
        return;
    }
    
    const weekdays = ['', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"];
    
    let bodyHTML = '';
    botSchedules.forEach(botSchedule => {
        const schedule = botSchedule.schedule;
        const statusClass = botSchedule.enabled ? 'success' : 'warning';
        const statusIcon = botSchedule.enabled ? 'check-circle' : 'pause-circle';
        
        bodyHTML += `
            <tr>
                <td>${schedule.club_name}</td>
                <td>${schedule.teacher_name}</td>
                <td>
                    <div>${weekdays[schedule.weekday]}</div>
                    <small class="text-muted">${schedule.start_time}</small>
                </td>
                <td>${schedule.group_name || '-'}</td>
                <td>
                    <span class="badge bg-info">${botSchedule.notification_time_description}</span>
                </td>
                <td>
                    <span class="badge bg-${statusClass}">
                        <i class="bi bi-${statusIcon}"></i> ${botSchedule.status_description}
                    </span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="viewBotSchedule(${botSchedule.id})" title="Переглянути">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-warning"
                                onclick="editBotSchedule(${botSchedule.id})" title="Редагувати">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm ${botSchedule.enabled ? 'btn-outline-warning' : 'btn-outline-success'}"
                                onclick="toggleBotSchedule(${botSchedule.id})" title="${botSchedule.enabled ? 'Вимкнути' : 'Увімкнути'}">
                            <i class="bi bi-${botSchedule.enabled ? 'pause' : 'play'}"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="deleteBotSchedule(${botSchedule.id})" title="Видалити">
                            <i class="bi bi-trash"></i>
                        </button>
            </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = bodyHTML;
}

// Фільтрація розсилок боту
function filterBotSchedules() {
    const statusFilter = document.getElementById('filterStatus').value;
    const clubFilter = document.getElementById('filterClub').value.toLowerCase();
    const teacherFilter = document.getElementById('filterTeacher').value.toLowerCase();
    const weekdayFilter = document.getElementById('filterWeekday').value;
    
    const filteredSchedules = allBotSchedules.filter(botSchedule => {
        const schedule = botSchedule.schedule;
        
        // Фільтр по статусу
        if (statusFilter) {
            if (statusFilter === 'enabled' && !botSchedule.enabled) return false;
            if (statusFilter === 'disabled' && botSchedule.enabled) return false;
        }
        
        // Фільтр по гуртку
        if (clubFilter && !schedule.club_name.toLowerCase().includes(clubFilter)) return false;
        
        // Фільтр по вчителю
        if (teacherFilter && !schedule.teacher_name.toLowerCase().includes(teacherFilter)) return false;
        
        // Фільтр по дню тижня
        if (weekdayFilter && schedule.weekday.toString() !== weekdayFilter) return false;
        
        return true;
    });
    
    displayBotSchedules(filteredSchedules);
}

// Відкриття модалки додавання розсилки
async function openAddBotScheduleModal() {
    try {
        showLoading(true);
        
        // Завантажуємо доступні розклади без розсилок
        const availableSchedules = allAvailableSchedules.filter(s => !s.has_bot_schedule);
        
        if (availableSchedules.length === 0) {
            showAlert('Всі активні розклади вже мають налаштовані розсилки боту', 'info');
            return;
        }
        
        const scheduleSelect = document.getElementById('scheduleSelect');
        scheduleSelect.innerHTML = '<option value="">Оберіть розклад</option>';
        
        const weekdays = ['', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"];
        
        availableSchedules.forEach(schedule => {
            const option = document.createElement('option');
            option.value = schedule.id;
            option.textContent = `${schedule.club_name} - ${schedule.teacher_name} (${weekdays[schedule.weekday]} ${schedule.start_time})`;
            scheduleSelect.appendChild(option);
        });
        
        // Очищаємо форму
        document.getElementById('addBotScheduleForm').reset();
        document.getElementById('offsetMinutes').value = '0';
        document.getElementById('enabledCheck').checked = true;
        
        const modal = new bootstrap.Modal(document.getElementById('addBotScheduleModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error opening add bot schedule modal:', error);
        showAlert('Помилка відкриття модалки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Збереження нової розсилки боту
async function saveBotSchedule() {
    const form = document.getElementById('addBotScheduleForm');
    const formData = new FormData(form);
    
    const scheduleId = formData.get('scheduleId');
    if (!scheduleId) {
        showAlert('Будь ласка, оберіть розклад', 'warning');
        return;
    }
    
    // Перевіряємо режим часу
    const exactMode = document.getElementById('exactMode').checked;
    let offsetMinutes = 0;
    let customTime = null;
    
    if (exactMode) {
        // Точний час
        customTime = document.getElementById('customTime').value;
        if (!customTime) {
            showAlert('Будь ласка, вкажіть точний час розсилки', 'warning');
            return;
        }
    } else {
        // Відносний час
    const customOffset = document.getElementById('customOffset').value;
        offsetMinutes = customOffset ? parseInt(customOffset) : parseInt(formData.get('offsetMinutes') || '0');
    }
    
    const botScheduleData = {
        schedule_id: parseInt(scheduleId),
        enabled: document.getElementById('enabledCheck').checked,
        offset_minutes: offsetMinutes,
        custom_time: customTime,
        custom_message: formData.get('customMessage') || null
    };
    
    try {
        showLoading(true);
        await apiCall('bot/schedules', 'POST', botScheduleData);
        
        bootstrap.Modal.getInstance(document.getElementById('addBotScheduleModal')).hide();
        showAlert('Розсилку боту успішно створено', 'success');
        
        // Перезавантажуємо дані
        await loadBotData();
        
    } catch (error) {
        console.error('Error saving bot schedule:', error);
        showAlert('Помилка створення розсилки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Редагування розсилки боту
async function editBotSchedule(botScheduleId) {
    try {
        showLoading(true);
        
        const botSchedule = await apiCall(`bot/schedules/${botScheduleId}`);
        
        document.getElementById('editBotScheduleId').value = botSchedule.id;
        document.getElementById('editCustomMessage').value = botSchedule.custom_message || '';
        document.getElementById('editEnabledCheck').checked = botSchedule.enabled;
        
        // Встановлюємо режим часу та відповідні значення
        if (botSchedule.custom_time) {
            // Точний час
            document.getElementById('editExactMode').checked = true;
            document.getElementById('editCustomTime').value = botSchedule.custom_time;
            document.getElementById('editOffsetMinutes').value = '0';
            document.getElementById('editCustomOffset').value = '';
            toggleEditTimeMode(); // Показуємо секцію точного часу
        } else {
            // Відносний час
            document.getElementById('editOffsetMode').checked = true;
            document.getElementById('editOffsetMinutes').value = botSchedule.offset_minutes.toString();
            document.getElementById('editCustomOffset').value = '';
            document.getElementById('editCustomTime').value = '';
            toggleEditTimeMode(); // Показуємо секцію offset
        }
        
        // Відображаємо інформацію про розклад
        const weekdays = ['', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"];
        document.getElementById('scheduleInfo').innerHTML = `
            <strong>${botSchedule.schedule.club_name}</strong> - ${botSchedule.schedule.teacher_name}<br>
            <small class="text-muted">${weekdays[botSchedule.schedule.weekday]} о ${botSchedule.schedule.start_time}</small>
        `;
        
        const modal = new bootstrap.Modal(document.getElementById('editBotScheduleModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading bot schedule for edit:', error);
        showAlert('Помилка завантаження розсилки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Оновлення розсилки боту
async function updateBotSchedule() {
    const botScheduleId = document.getElementById('editBotScheduleId').value;
    
    // Перевіряємо режим часу
    const exactMode = document.getElementById('editExactMode').checked;
    let offsetMinutes = 0;
    let customTime = null;
    
    if (exactMode) {
        // Точний час
        customTime = document.getElementById('editCustomTime').value;
        if (!customTime) {
            showAlert('Будь ласка, вкажіть точний час розсилки', 'warning');
            return;
        }
    } else {
        // Відносний час
    const customOffset = document.getElementById('editCustomOffset').value;
        offsetMinutes = customOffset ? parseInt(customOffset) : parseInt(document.getElementById('editOffsetMinutes').value);
    }
    
    const updateData = {
        enabled: document.getElementById('editEnabledCheck').checked,
        offset_minutes: offsetMinutes,
        custom_time: customTime,
        custom_message: document.getElementById('editCustomMessage').value || null
    };
    
    try {
        showLoading(true);
        await apiCall(`bot/schedules/${botScheduleId}`, 'PUT', updateData);
        
        bootstrap.Modal.getInstance(document.getElementById('editBotScheduleModal')).hide();
        showAlert('Розсилку боту успішно оновлено', 'success');
        
        // Перезавантажуємо дані
        await loadBotData();
        
    } catch (error) {
        console.error('Error updating bot schedule:', error);
        showAlert('Помилка оновлення розсилки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Перемикання статусу розсилки
async function toggleBotSchedule(botScheduleId) {
    const botSchedule = allBotSchedules.find(bs => bs.id === botScheduleId);
    if (!botSchedule) return;
    
    const newStatus = !botSchedule.enabled;
    const action = newStatus ? 'увімкнути' : 'вимкнути';
    
    if (!confirm(`Ви впевнені, що хочете ${action} цю розсилку?`)) {
        return;
    }
    
    try {
        showLoading(true);
        await apiCall(`bot/schedules/${botScheduleId}`, 'PUT', { enabled: newStatus });
        
        showAlert(`Розсилку успішно ${newStatus ? 'увімкнено' : 'вимкнено'}`, 'success');
        
        // Перезавантажуємо дані
        await loadBotData();
        
    } catch (error) {
        console.error('Error toggling bot schedule:', error);
        showAlert('Помилка зміни статусу розсилки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Видалення розсилки боту
async function deleteBotSchedule(botScheduleId) {
    if (!confirm('Ви впевнені, що хочете видалити цю розсилку боту? Ця дія незворотна.')) {
        return;
    }
    
    try {
        showLoading(true);
        await apiCall(`bot/schedules/${botScheduleId}`, 'DELETE');
        
        showAlert('Розсилку боту успішно видалено', 'success');
        
        // Перезавантажуємо дані
        await loadBotData();
        
    } catch (error) {
        console.error('Error deleting bot schedule:', error);
        showAlert('Помилка видалення розсилки: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Перегляд розсилки боту
function viewBotSchedule(botScheduleId) {
    const botSchedule = allBotSchedules.find(bs => bs.id === botScheduleId);
    if (!botSchedule) return;
    
    const weekdays = ['', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"];
    
    showAlert(`
        <strong>Інформація про розсилку:</strong><br>
        <strong>Гурток:</strong> ${botSchedule.schedule.club_name}<br>
        <strong>Вчитель:</strong> ${botSchedule.schedule.teacher_name}<br>
        <strong>Розклад:</strong> ${weekdays[botSchedule.schedule.weekday]} о ${botSchedule.schedule.start_time}<br>
        <strong>Час розсилки:</strong> ${botSchedule.notification_time_description}<br>
        <strong>Статус:</strong> ${botSchedule.status_description}<br>
        ${botSchedule.custom_message ? `<strong>Повідомлення:</strong> ${botSchedule.custom_message}` : ''}
    `, 'info');
}

// Функції для переключення режимів часу
function toggleTimeMode() {
    const offsetMode = document.getElementById('offsetMode').checked;
    const offsetSection = document.getElementById('offsetSection');
    const exactTimeSection = document.getElementById('exactTimeSection');
    
    if (offsetMode) {
        offsetSection.style.display = 'block';
        exactTimeSection.style.display = 'none';
        // Очищуємо точний час
        document.getElementById('customTime').value = '';
    } else {
        offsetSection.style.display = 'none';
        exactTimeSection.style.display = 'block';
        // Очищуємо offset
        document.getElementById('offsetMinutes').value = '0';
        document.getElementById('customOffset').value = '';
    }
}

function toggleEditTimeMode() {
    const offsetMode = document.getElementById('editOffsetMode').checked;
    const offsetSection = document.getElementById('editOffsetSection');
    const exactTimeSection = document.getElementById('editExactTimeSection');
    
    if (offsetMode) {
        offsetSection.style.display = 'block';
        exactTimeSection.style.display = 'none';
        // Очищуємо точний час
        document.getElementById('editCustomTime').value = '';
    } else {
        offsetSection.style.display = 'none';
        exactTimeSection.style.display = 'block';
        // Очищуємо offset
        document.getElementById('editOffsetMinutes').value = '0';
        document.getElementById('editCustomOffset').value = '';
    }
}

// === TEACHERS EXCEL IMPORT FUNCTIONS ===

// Скачування шаблону Excel для вчителів
async function downloadTeachersTemplate() {
    try {
        showLoading(true);
        
        // ТИМЧАСОВЕ РІШЕННЯ: використовуємо шаблон учнів для демонстрації
        const response = await fetch('/api/students/template/download');
        if (!response.ok) {
            throw new Error('Помилка при завантаженні шаблону');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'teachers_template.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Шаблон Excel для вчителів завантажено!', 'success');
        
    } catch (error) {
        console.error('Error downloading teachers template:', error);
        showAlert('Помилка при завантаженні шаблону: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Імпорт вчителів з Excel файлу
async function importTeachers() {
    const fileInput = document.getElementById('teachersExcelFile');
    const skipDuplicates = document.getElementById('skipTeachersDuplicates').checked;
    
    if (!fileInput.files.length) {
        showAlert('Будь ласка, виберіть Excel файл для імпорту вчителів', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Перевіряємо формат файлу
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        showAlert('Будь ласка, виберіть файл Excel (.xlsx або .xls)', 'warning');
        return;
    }
    
    try {
        // Показуємо прогрес
        showImportTeachersProgress(true);
        updateImportTeachersProgress(10, 'Підготовка до імпорту вчителів...');
        
        // Створюємо FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('skip_duplicates', skipDuplicates);
        
        updateImportTeachersProgress(30, 'Завантаження файлу...');
        
        // Відправляємо запит
        const response = await fetch('/api/teachers/import', {
            method: 'POST',
            body: formData
        });
        
        updateImportTeachersProgress(70, 'Обробка даних вчителів...');
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Помилка при імпорті файлу вчителів');
        }
        
        const result = await response.json();
        updateImportTeachersProgress(100, 'Завершено!');
        
        // Показуємо результати
        showImportTeachersResults(result);
        
        // Оновлюємо таблицю вчителів
        if (result.created_count > 0) {
            await loadTeachersData();
        }
        
    } catch (error) {
        console.error('Error importing teachers:', error);
        showAlert('Помилка при імпорті вчителів: ' + error.message, 'danger');
        hideImportTeachersProgress();
    }
}

// Показати прогрес імпорту вчителів
function showImportTeachersProgress(show = true) {
    const progressDiv = document.getElementById('importTeachersProgress');
    const resultsDiv = document.getElementById('importTeachersResults');
    
    if (show) {
        progressDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
    } else {
        progressDiv.style.display = 'none';
    }
}

// Сховати прогрес імпорту вчителів
function hideImportTeachersProgress() {
    showImportTeachersProgress(false);
}

// Оновити прогрес імпорту вчителів
function updateImportTeachersProgress(percent, message) {
    const progressBar = document.querySelector('#importTeachersProgress .progress-bar');
    const statusText = document.getElementById('importTeachersStatus');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
    }
    
    if (statusText) {
        statusText.textContent = message;
    }
}

// Показати результати імпорту вчителів
function showImportTeachersResults(result) {
    const resultsDiv = document.getElementById('importTeachersResults');
    const summaryDiv = document.getElementById('importTeachersSummary');
    
    hideImportTeachersProgress();
    
    let summaryHTML = `
        <div class="row">
            <div class="col-md-4">
                <div class="text-center">
                    <h6 class="text-success">${result.created_count}</h6>
                    <small>Створено</small>
                </div>
            </div>
            <div class="col-md-4">
                <div class="text-center">
                    <h6 class="text-warning">${result.skipped_count}</h6>
                    <small>Пропущено</small>
                </div>
            </div>
            <div class="col-md-4">
                <div class="text-center">
                    <h6 class="text-danger">${result.errors.length}</h6>
                    <small>Помилок</small>
                </div>
            </div>
        </div>
    `;
    
    if (result.errors.length > 0) {
        summaryHTML += `
            <div class="mt-3">
                <h6 class="text-danger">Помилки:</h6>
                <ul class="mb-0">
                    ${result.errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    summaryDiv.innerHTML = summaryHTML;
    resultsDiv.style.display = 'block';
    
    // Показуємо загальне повідомлення
    if (result.created_count > 0) {
        showAlert(`Успішно імпортовано ${result.created_count} вчителів!`, 'success');
    }
}

// === EXCEL EXPORT FUNCTIONS ===

// Експорт учнів з повною інформацією
async function exportStudentsExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/students/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті учнів');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'students_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Дані учнів експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting students:', error);
        showAlert('Помилка при експорті учнів: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Експорт вчителів
async function exportTeachersExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/teachers/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті вчителів');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'teachers_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Дані вчителів експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting teachers:', error);
        showAlert('Помилка при експорті вчителів: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Експорт гуртків
async function exportClubsExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/clubs/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті гуртків');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'clubs_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Дані гуртків експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting clubs:', error);
        showAlert('Помилка при експорті гуртків: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Експорт розкладів
async function exportSchedulesExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/schedules/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті розкладів');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'schedules_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Розклади експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting schedules:', error);
        showAlert('Помилка при експорті розкладів: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Експорт проведених уроків
async function exportConductedLessonsExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/conducted-lessons/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті проведених уроків');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'conducted_lessons_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Проведені уроки експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting conducted lessons:', error);
        showAlert('Помилка при експорті проведених уроків: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Експорт зарплат
async function exportPayrollExcel() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/payroll/export/excel');
        if (!response.ok) {
            throw new Error('Помилка при експорті зарплат');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'payroll_export.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showAlert('Зарплати експортовано в Excel!', 'success');
        
    } catch (error) {
        console.error('Error exporting payroll:', error);
        showAlert('Помилка при експорті зарплат: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Допоміжні функції для offset
function updateOffsetSelect() {
    const customOffset = document.getElementById('customOffset').value;
    if (customOffset) {
        document.getElementById('offsetMinutes').value = customOffset;
    }
}

function updateEditOffsetSelect() {
    const customOffset = document.getElementById('editCustomOffset').value;
    if (customOffset) {
        document.getElementById('editOffsetMinutes').value = customOffset;
    }
}