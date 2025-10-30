// Уніфікований API модуль для School of Life
// Всі запити йдуть через /api/public без аутентифікації

window.API = (window.__API_BASE__ ?? (window.location.origin + "/api/public"));

window.j = (u) => (u.startsWith("http") ? u : window.API + (u.startsWith("/") ? u : "/" + u));

window.req = async function(path, opt = {}) {
    const url = window.j(path);
    const options = {
        headers: {
            "Content-Type": "application/json",
            ...(opt.headers || {})
        },
        ...opt
    };
    
    console.log(`API ${opt.method || "GET"} ${url}`);
    
    try {
        const r = await fetch(url, options);
        
        if (!r.ok) {
            const errorText = await r.text().catch(() => 'Unknown error');
            throw new Error(`API ${opt.method || "GET"} ${url} -> ${r.status}: ${errorText}`);
        }
        
        // Для DELETE запитів може не бути JSON
        if (r.status === 204) {
            return null;
        }
        
        return await r.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Готові функції для CRUD операцій
window.api = {
    // Студенти
    students: {
        list: () => req("students"),
        get: (id) => req(`students/${id}`),
        create: (data) => req("students", {method: "POST", body: JSON.stringify(data)}),
        update: (id, data) => req(`students/${id}`, {method: "PUT", body: JSON.stringify(data)}),
        delete: (id) => req(`students/${id}`, {method: "DELETE"})
    },
    
    // Вчителі
    teachers: {
        list: () => req("teachers"),
        get: (id) => req(`teachers/${id}`),
        create: (data) => req("teachers", {method: "POST", body: JSON.stringify(data)}),
        update: (id, data) => req(`teachers/${id}`, {method: "PUT", body: JSON.stringify(data)}),
        delete: (id) => req(`teachers/${id}`, {method: "DELETE"})
    },
    
    // Гуртки
    clubs: {
        list: () => req("clubs"),
        get: (id) => req(`clubs/${id}`),
        create: (data) => req("clubs", {method: "POST", body: JSON.stringify(data)}),
        update: (id, data) => req(`clubs/${id}`, {method: "PUT", body: JSON.stringify(data)}),
        delete: (id) => req(`clubs/${id}`, {method: "DELETE"})
    }
};