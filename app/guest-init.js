/**
 * Guest Mode Initialization
 * Auto-joins room when coming from guest link
 */

window.addEventListener('load', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const isGuest = urlParams.get('guest') === 'true';
    const roomId = urlParams.get('room');
    const guestParticipantId = urlParams.get('participant');
    const guestName = urlParams.get('name');
    const guestLang = urlParams.get('lang');
    
    if (isGuest && roomId && guestParticipantId && guestName) {
        console.log('👤 Guest mode activated:', { roomId, guestName, guestLang });
        
        // Wait for app.js to fully load
        setTimeout(() => {
            // Access global variables from app.js
            if (typeof currentRoom !== 'undefined') {
                // app.js loaded, set global variables directly
                currentRoom = roomId;
                participantId = guestParticipantId;
                participantName = guestName;
                isHost = false;
            }
            
            // Set language if provided
            const sourceLangSelect = document.getElementById('sourceLang');
            if (guestLang && sourceLangSelect) {
                sourceLangSelect.value = guestLang;
            }
            
            // Show room info
            const roomCodeElem = document.getElementById('roomCode');
            const roomInfoElem = document.getElementById('roomInfo');
            if (roomCodeElem) {
                roomCodeElem.textContent = `Guest in room: ${roomId}`;
                roomCodeElem.style.fontSize = '1rem';
            }
            if (roomInfoElem) roomInfoElem.style.display = 'flex';
            
            // Hide room creation buttons
            const createBtn = document.getElementById('createRoomBtn');
            const joinBtn = document.getElementById('joinRoomBtn');
            if (createBtn) createBtn.style.display = 'none';
            if (joinBtn) joinBtn.style.display = 'none';
            
            // Show guest banner
            if (window.showToast) {
                window.showToast(`👤 Joined as guest: ${guestName}. Host is paying. You can see and use all features!`, 'info', 7000);
            }
            
            // Hide user info bar (guests don't have accounts)
            const userInfo = document.getElementById('user-info');
            if (userInfo) userInfo.style.display = 'none';
            
            // Auto-connect to room
            if (typeof connectToRoom === 'function') {
                setTimeout(() => connectToRoom(), 1000);
            }
        }, 500);
    }
});

