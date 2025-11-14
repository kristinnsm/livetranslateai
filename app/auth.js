// Google OAuth Configuration
const GOOGLE_CLIENT_ID = '712731007087-jmc0mscl0jrknp86hl7kjgqi6uk2q5v7.apps.googleusercontent.com';

// Free tier limit
const FREE_MINUTES_LIMIT = 15; // Reduced from 30 to prevent abuse

// Current user state
let currentUser = null;

// Generate device fingerprint for abuse prevention
function getDeviceFingerprint() {
    const data = {
        screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language,
        platform: navigator.platform,
        hardwareConcurrency: navigator.hardwareConcurrency || 0,
        deviceMemory: navigator.deviceMemory || 0,
        userAgent: navigator.userAgent.substring(0, 150)
    };
    
    // Simple hash function
    const str = JSON.stringify(data);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return `fp_${Math.abs(hash)}`;
}

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
        
        // Generate device fingerprint
        const fingerprint = getDeviceFingerprint();
        console.log('🔒 Device fingerprint generated:', fingerprint);
        
        // Send token to backend for verification
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const result = await fetch(`${backendUrl}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                token: credential,
                fingerprint: fingerprint
            })
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
            // Handle specific error cases
            // Fingerprint blocking removed - Stripe protects via free trial limits
            throw new Error(data.error || 'Login failed');
        }
    } catch (error) {
        console.error('❌ Login error:', error);
        showToast('Login failed: ' + error.message, 'error');
    } finally {
        showAuthLoading(false);
    }
}

// Check if user is already logged in OR if guest mode
function checkAuthStatus() {
    // Check if guest mode (from URL params)
    const urlParams = new URLSearchParams(window.location.search);
    const isGuest = urlParams.get('guest') === 'true';
    
    if (isGuest) {
        console.log('👤 Guest mode detected - bypassing auth');
        // Hide auth overlay for guests
        const authContainer = document.getElementById('auth-container');
        if (authContainer) authContainer.style.display = 'none';
        return true; // Allow access
    }
    
    // Normal auth check
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
    const userInfo = document.getElementById('user-info');
    
    console.log('🎨 Updating UI, logged in:', isLoggedIn, 'User:', currentUser);
    
    if (isLoggedIn && currentUser) {
        // Hide auth overlay
        if (authContainer) {
            authContainer.style.display = 'none';
        }
        
        // Show user info bar
        if (userInfo) {
            userInfo.style.display = 'block';
            
            // Determine tier display
            let tierDisplay = '';
            if (currentUser.tier === 'premium') {
                tierDisplay = '<div class="user-tier" style="color: #10B981;">✨ Premium - Unlimited calls</div>';
            } else if (currentUser.minutes_used > FREE_MINUTES_LIMIT) {
                tierDisplay = `<div class="user-tier" style="color: #EF4444;">Free Tier - Over limit (${currentUser.minutes_used.toFixed(1)} min used)</div>`;
            } else {
                tierDisplay = `<div class="user-tier">Free Tier - ${(FREE_MINUTES_LIMIT - currentUser.minutes_used).toFixed(1)} min remaining</div>`;
            }
            
            // Add appropriate action button based on tier
            let actionButton = '';
            if (currentUser.tier === 'premium') {
                // Premium users: Show "Manage Subscription" button
                actionButton = '<button onclick="auth.openCustomerPortal()" class="btn-manage" style="background: #4F46E5; color: white; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.85rem; cursor: pointer; margin-right: 0.5rem;">Manage Subscription</button>';
            } else {
                // Free users: Show "Upgrade Now" button (always visible)
                actionButton = '<button onclick="showUpgradeModal()" class="btn-upgrade-now" style="background: linear-gradient(135deg, #8B5CF6 0%, #4F46E5 100%); color: white; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.85rem; cursor: pointer; margin-right: 0.5rem; font-weight: 600;">💎 Upgrade Now</button>';
            }
            
            userInfo.innerHTML = `
                <div class="user-profile">
                    <img src="${currentUser.picture}" alt="${currentUser.name}" class="user-avatar">
                    <div class="user-details">
                        <div class="user-name">${currentUser.name}</div>
                        <div class="user-email">${currentUser.email}</div>
                        ${tierDisplay}
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        ${actionButton}
                        <button onclick="auth.logout()" class="btn-logout">Logout</button>
                    </div>
                </div>
            `;
            console.log('✅ User info displayed');
        } else {
            console.warn('⚠️ User info element not found');
        }
    } else {
        // Show login overlay
        if (authContainer) {
            authContainer.style.display = 'flex';
        }
        if (userInfo) {
            userInfo.style.display = 'none';
            userInfo.innerHTML = '';
        }
    }
}

// Update usage display
function updateUsageDisplay(user) {
    const usageContainer = document.getElementById('usage-display');
    if (!usageContainer) return;
    
    const minutesUsed = user.minutes_used || 0;
    const minutesLimit = user.tier === 'free' ? FREE_MINUTES_LIMIT : 999999; // 15 for free, unlimited for paid
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
            <span class="usage-label">⏱️ Usage</span>
            <div class="usage-bar">
                <div class="usage-progress" style="width: ${percentage}%"></div>
            </div>
            <span class="usage-text">${minutesUsed.toFixed(1)} / ${minutesLimit} min</span>
            <span class="usage-status">${statusText}</span>
        </div>
        ${percentage >= 80 ? `
            <button onclick="showUpgradeModal()" class="btn-upgrade">
                ${percentage >= 100 ? '🚀 Upgrade Now' : '💎 Get Unlimited'}
            </button>
        ` : ''}
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

// Show upgrade modal (beautiful UI, not ugly alert)
function showUpgradeModal() {
    // Show modal (no need to update minutes - we removed that confusing text)
    const modal = document.getElementById('upgradeModal');
    if (modal) {
        modal.style.display = 'flex';
        console.log('🎉 Showing upgrade modal');
    }
    
    // Set up button handlers (only once)
    const upgradeBtn = document.getElementById('upgradeNowBtn');
    const laterBtn = document.getElementById('upgradeLaterBtn');
    
    if (upgradeBtn && !upgradeBtn.hasClickListener) {
        upgradeBtn.addEventListener('click', async () => {
            console.log('💳 User clicked Start Free Trial');
            upgradeBtn.disabled = true;
            upgradeBtn.textContent = 'Loading...';
            
            try {
                await startStripeCheckout();
            } catch (error) {
                console.error('❌ Stripe checkout error:', error);
                alert('Failed to start checkout. Please try again or contact support.');
                upgradeBtn.disabled = false;
                upgradeBtn.textContent = 'Start Free Trial';
            }
        });
        upgradeBtn.hasClickListener = true;
    }
    
    if (laterBtn && !laterBtn.hasClickListener) {
        laterBtn.addEventListener('click', () => {
            console.log('⏭️ User clicked Maybe Later');
            hideUpgradeModal();
        });
        laterBtn.hasClickListener = true;
    }
}

function hideUpgradeModal() {
    const modal = document.getElementById('upgradeModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Abuse modal removed - Stripe protects via free trial limits (one trial per card)

// Initialize on page load
window.addEventListener('load', () => {
    console.log('🚀 Auth system initializing...');
    
    // Check if already logged in
    const isLoggedIn = checkAuthStatus();
    
    // If not logged in, init Google button
    if (!isLoggedIn) {
        initGoogleAuth();
    } else {
        // If logged in, refresh usage every 30 seconds
        setInterval(async () => {
            if (isAuthenticated()) {
                await refreshUsage();
            }
        }, 30000); // Every 30 seconds
    }
});

// Fetch latest usage from backend
async function refreshUsage() {
    const user = getCurrentUser();
    if (!user) return null;
    
    try {
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const response = await fetch(`${backendUrl}/api/user/usage?user_id=${user.user_id}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            const usageData = await response.json();
            
            // Update stored user with latest usage
            currentUser.minutes_used = usageData.minutes_used;
            localStorage.setItem('user', JSON.stringify(currentUser));
            
            // Update displays
            updateAuthUI(true);
            updateUsageDisplay(currentUser);
            
            console.log(`📊 Usage refreshed: ${usageData.minutes_used}/${usageData.minutes_limit} min`);
            
            return usageData;
        }
    } catch (error) {
        console.error('❌ Failed to refresh usage:', error);
    }
    
    return null;
}

// Check if user can start a call
async function canStartCall() {
    const user = getCurrentUser();
    if (!user) {
        alert('Please login first');
        return false;
    }
    
    // Refresh usage from backend
    const usageData = await refreshUsage();
    
    if (!usageData) {
        // Couldn't get usage, allow call (fail open)
        return true;
    }
    
    if (!usageData.can_use) {
        // Show upgrade modal
        showUpgradeModal();
        return false;
    }
    
    return true;
}

// Stripe Integration
async function startStripeCheckout() {
    const user = getCurrentUser();
    if (!user) {
        throw new Error('User not logged in');
    }
    
    const backendUrl = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'
        : 'https://livetranslateai.onrender.com';
    
    const frontendUrl = window.location.hostname === 'localhost'
        ? 'http://localhost:3000'
        : window.location.origin;
    
    console.log('💳 Creating Stripe checkout session...');
    
    const response = await fetch(`${backendUrl}/api/stripe/create-checkout-session`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({
            user_id: user.user_id,
            frontend_url: frontendUrl
        })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create checkout session');
    }
    
    const data = await response.json();
    
    console.log('✅ Checkout session created, redirecting to Stripe...');
    
    // Redirect to Stripe Checkout
    window.location.href = data.checkout_url;
}

async function openCustomerPortal() {
    const user = getCurrentUser();
    if (!user) {
        alert('Please login first');
        return;
    }
    
    const backendUrl = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'
        : 'https://livetranslateai.onrender.com';
    
    const frontendUrl = window.location.hostname === 'localhost'
        ? 'http://localhost:3000'
        : window.location.origin;
    
    console.log('🔧 Opening Stripe Customer Portal...', { user_id: user.user_id, email: user.email });
    
    try {
        const response = await fetch(`${backendUrl}/api/stripe/create-portal-session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                user_id: user.user_id,
                frontend_url: frontendUrl
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            console.error('❌ Portal API error:', error);
            
            // More helpful error messages
            if (response.status === 404) {
                alert('⚠️ Subscription not found. This can happen if:\n\n1. Your payment just completed (wait 30 seconds)\n2. Your trial was cancelled\n\nPlease try logging out and back in. If this persists, contact support@livetranslateai.com');
            } else {
                throw new Error(error.error || 'Failed to open portal');
            }
            return;
        }
        
        const data = await response.json();
        console.log('✅ Portal URL received, redirecting...');
        
        // Redirect to Stripe Customer Portal
        window.location.href = data.portal_url;
    } catch (error) {
        console.error('❌ Portal error:', error);
        alert('Failed to open subscription management. Please try again or contact support@livetranslateai.com');
    }
}

// Handle payment status from URL parameters
function handlePaymentStatus() {
    const urlParams = new URLSearchParams(window.location.search);
    const payment = urlParams.get('payment');
    
    if (payment === 'success') {
        console.log('✅ Payment successful! Refreshing user data...');
        
        // Retry logic: Check up to 5 times with increasing delays
        // Webhook might take a few seconds to process
        const refreshUserData = async (attempt = 1, maxAttempts = 5) => {
            console.log(`🔄 Attempting data refresh (attempt ${attempt}/${maxAttempts})...`);
            
            const authToken = localStorage.getItem('auth_token');
            const userStr = localStorage.getItem('user');
            
            if (!userStr) {
                console.error('❌ No user data found in localStorage');
                return;
            }
            
            const user = JSON.parse(userStr);
            const backendUrl = window.location.hostname === 'localhost' 
                ? 'http://localhost:8000'
                : 'https://livetranslateai.onrender.com';
            
            try {
                const response = await fetch(`${backendUrl}/api/user/usage?user_id=${user.user_id}`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                
                if (response.ok) {
                    const freshData = await response.json();
                    console.log('🔄 Fresh user data:', freshData);
                    
                    // Check if tier was updated to premium
                    if (freshData.tier === 'premium') {
                        console.log('✅ Premium tier confirmed! Updating UI...');
                        
                        // Update localStorage with fresh tier
                        user.tier = freshData.tier;
                        user.minutes_used = freshData.minutes_used;
                        localStorage.setItem('user', JSON.stringify(user));
                        currentUser = user;
                        
                        // Force UI update
                        updateAuthUI(true);
                        
                        // Show success modal
                        showPaymentSuccessModal();
                        
                        // Clean URL
                        window.history.replaceState({}, document.title, window.location.pathname);
                        return; // Success! Exit retry loop
                    } else {
                        // Still showing as free, retry if we have attempts left
                        if (attempt < maxAttempts) {
                            const delay = attempt * 2000; // 2s, 4s, 6s, 8s, 10s
                            console.log(`⏳ Tier still "free", retrying in ${delay}ms...`);
                            setTimeout(() => refreshUserData(attempt + 1, maxAttempts), delay);
                        } else {
                            console.warn('⚠️ Max retries reached. Tier still showing as "free".');
                            // Show success modal anyway (webhook might be delayed)
                            showPaymentSuccessModal();
                            showToast('Payment successful! If your account doesn\'t show Premium, please refresh the page in a few seconds.', 'info', 8000);
                            window.history.replaceState({}, document.title, window.location.pathname);
                        }
                    }
                } else {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
            } catch (error) {
                console.error(`❌ Failed to refresh user data (attempt ${attempt}):`, error);
                
                if (attempt < maxAttempts) {
                    const delay = attempt * 2000;
                    setTimeout(() => refreshUserData(attempt + 1, maxAttempts), delay);
                } else {
                    // Final fallback
                    showToast('Payment successful! Please refresh the page to see your Premium status.', 'info', 8000);
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            }
        };
        
        // Start refresh after initial delay (webhook needs time to process)
        setTimeout(() => refreshUserData(), 3000); // Wait 3 seconds for webhook to process
        
    } else if (payment === 'cancelled') {
        console.log('❌ Payment cancelled');
        // Show cancelled message with toast (not ugly alert)
        setTimeout(() => {
            showToast('Payment cancelled. You can upgrade anytime from your profile.', 'info', 5000);
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }, 1000);
    }
}

// Show payment success modal (beautiful custom UI)
function showPaymentSuccessModal() {
    const modalHTML = `
        <div id="successModal" class="upgrade-modal-overlay" style="display: flex;">
            <div class="upgrade-modal" style="max-width: 500px;">
                <div class="upgrade-modal-header" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);">
                    <div class="upgrade-modal-icon">🎉</div>
                    <h2>Welcome to LiveTranslateAI Pro!</h2>
                    <p>Your 7-day free trial has started</p>
                </div>
                <div class="upgrade-modal-body">
                    <p style="text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 1.5rem; font-weight: 600;">
                        ✨ You now have unlimited calls! ✨
                    </p>
                    <ul class="benefits-list">
                        <li>Unlimited translation minutes</li>
                        <li>All 15 languages included</li>
                        <li>HD video calls</li>
                        <li>No charge for 7 days</li>
                        <li>Then $29/month (cancel anytime)</li>
                    </ul>
                    <p style="text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 1.5rem;">
                        Manage your subscription anytime from your profile
                    </p>
                    <div class="upgrade-modal-actions">
                        <button onclick="hideSuccessModal()" class="btn-upgrade-primary" style="width: 100%;">Start Using Pro! 🚀</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add to page
    if (!document.getElementById('successModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    } else {
        document.getElementById('successModal').style.display = 'flex';
    }
}

function hideSuccessModal() {
    const modal = document.getElementById('successModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.hideSuccessModal = hideSuccessModal;

// Export functions for use in app.js
window.auth = {
    getCurrentUser,
    isAuthenticated,
    getAuthToken,
    logout,
    updateUsageDisplay,
    checkAuthStatus,
    refreshUsage,
    canStartCall,
    startStripeCheckout,
    openCustomerPortal
};

// Check for payment status on load
handlePaymentStatus();

