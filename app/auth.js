// Google OAuth Configuration
const GOOGLE_CLIENT_ID = '712731007087-jmc0mscl0jrknp86hl7kjgqi6uk2q5v7.apps.googleusercontent.com';

// Current user state
let currentUser = null;

// Initialize Google Sign-In when page loads
function initGoogleAuth() {
    console.log('🔐 Initializing Google Auth...');
    
    // Load Google Identity Services script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
        console.log('✅ Google Identity Services loaded');
        renderGoogleButton();
    };
    document.head.appendChild(script);
}

// Render Google Sign-In button
function renderGoogleButton() {
    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLogin,
        auto_select: false,
        cancel_on_tap_outside: true,
    });
    
    // Render button in the auth container
    const buttonDiv = document.getElementById('google-signin-button');
    if (buttonDiv) {
        google.accounts.id.renderButton(
            buttonDiv,
            { 
                theme: 'outline',
                size: 'large',
                text: 'continue_with',
                shape: 'rectangular',
                width: 300
            }
        );
        console.log('✅ Google Sign-In button rendered');
    }
}

// Handle Google login response
async function handleGoogleLogin(response) {
    console.log('🔐 Google login response received');
    const credential = response.credential;
    
    try {
        // Show loading state
        showAuthLoading(true);
        
        // Send token to backend for verification
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const result = await fetch(`${backendUrl}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: credential })
        });
        
        const data = await result.json();
        
        if (data.success) {
            // Store session
            localStorage.setItem('auth_token', data.session_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            currentUser = data.user;
            
            console.log('✅ Login successful:', data.user.name);
            
            // Update UI
            updateAuthUI(true);
            showToast(`Welcome, ${data.user.name}!`, 'success');
            
            // Show usage info
            updateUsageDisplay(data.user);
            
        } else {
            throw new Error(data.error || 'Login failed');
        }
    } catch (error) {
        console.error('❌ Login error:', error);
        showToast('Login failed: ' + error.message, 'error');
    } finally {
        showAuthLoading(false);
    }
}

// Check if user is already logged in
function checkAuthStatus() {
    const token = localStorage.getItem('auth_token');
    const userStr = localStorage.getItem('user');
    
    if (token && userStr) {
        try {
            currentUser = JSON.parse(userStr);
            console.log('✅ User already logged in:', currentUser.name);
            updateAuthUI(true);
            updateUsageDisplay(currentUser);
            return true;
        } catch (e) {
            console.error('❌ Invalid stored user data');
            logout();
        }
    }
    
    updateAuthUI(false);
    return false;
}

// Update UI based on auth state
function updateAuthUI(isLoggedIn) {
    const authContainer = document.getElementById('auth-container');
    const appContainer = document.getElementById('app-container');
    const userInfo = document.getElementById('user-info');
    
    if (isLoggedIn && currentUser) {
        // Hide login, show app
        if (authContainer) authContainer.style.display = 'none';
        if (appContainer) appContainer.style.display = 'block';
        
        // Show user info
        if (userInfo) {
            userInfo.innerHTML = `
                <div class="user-profile">
                    <img src="${currentUser.picture}" alt="${currentUser.name}" class="user-avatar">
                    <div class="user-details">
                        <div class="user-name">${currentUser.name}</div>
                        <div class="user-email">${currentUser.email}</div>
                    </div>
                    <button onclick="logout()" class="btn-logout">Logout</button>
                </div>
            `;
        }
    } else {
        // Show login, hide app
        if (authContainer) authContainer.style.display = 'flex';
        if (appContainer) appContainer.style.display = 'none';
        if (userInfo) userInfo.innerHTML = '';
    }
}

// Update usage display
function updateUsageDisplay(user) {
    const usageContainer = document.getElementById('usage-display');
    if (!usageContainer) return;
    
    const minutesUsed = user.minutes_used || 0;
    const minutesLimit = user.tier === 'free' ? 30 : 999999; // 30 for free, unlimited for paid
    const percentage = Math.min((minutesUsed / minutesLimit) * 100, 100);
    
    let statusClass = 'usage-ok';
    let statusText = 'Available';
    
    if (percentage >= 100) {
        statusClass = 'usage-exceeded';
        statusText = 'Limit Reached';
    } else if (percentage >= 80) {
        statusClass = 'usage-warning';
        statusText = 'Running Low';
    }
    
    usageContainer.innerHTML = `
        <div class="usage-info ${statusClass}">
            <div class="usage-header">
                <span class="usage-label">Free Minutes</span>
                <span class="usage-status">${statusText}</span>
            </div>
            <div class="usage-bar">
                <div class="usage-progress" style="width: ${percentage}%"></div>
            </div>
            <div class="usage-text">
                ${minutesUsed.toFixed(1)} / ${minutesLimit} minutes used
            </div>
            ${percentage >= 80 ? `
                <button onclick="showUpgradeModal()" class="btn-upgrade">
                    ${percentage >= 100 ? 'Upgrade to Continue' : 'Get More Minutes'}
                </button>
            ` : ''}
        </div>
    `;
}

// Show loading state
function showAuthLoading(loading) {
    const button = document.getElementById('google-signin-button');
    if (button) {
        button.style.opacity = loading ? '0.5' : '1';
        button.style.pointerEvents = loading ? 'none' : 'auto';
    }
}

// Logout function
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    currentUser = null;
    
    console.log('👋 User logged out');
    updateAuthUI(false);
    showToast('Logged out successfully', 'info');
    
    // Reload page to reset state
    setTimeout(() => window.location.reload(), 1000);
}

// Get current user
function getCurrentUser() {
    return currentUser;
}

// Check if user is authenticated
function isAuthenticated() {
    return currentUser !== null;
}

// Get auth token
function getAuthToken() {
    return localStorage.getItem('auth_token');
}

// Show upgrade modal
function showUpgradeModal() {
    alert('Upgrade flow coming soon! This will redirect to Stripe checkout for 7-day trial.');
    // TODO: Implement Stripe checkout
}

// Initialize on page load
window.addEventListener('load', () => {
    console.log('🚀 Auth system initializing...');
    
    // Check if already logged in
    const isLoggedIn = checkAuthStatus();
    
    // If not logged in, init Google button
    if (!isLoggedIn) {
        initGoogleAuth();
    }
});

// Export functions for use in app.js
window.auth = {
    getCurrentUser,
    isAuthenticated,
    getAuthToken,
    logout,
    updateUsageDisplay,
    checkAuthStatus
};

