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
            // Set up guest session
            window.currentRoom = roomId;
            window.participantId = guestParticipantId;
            window.participantName = guestName;
            window.isHost = false;
            
            // Set language if provided
            const sourceLangSelect = document.getElementById('sourceLang');
            if (guestLang && sourceLangSelect) {
                sourceLangSelect.value = guestLang;
            }
            
            // Show room info
            const roomCodeElem = document.getElementById('roomCode');
            const roomInfoElem = document.getElementById('roomInfo');
            if (roomCodeElem) roomCodeElem.textContent = roomId;
            if (roomInfoElem) roomInfoElem.style.display = 'flex';
            
            // Hide room creation buttons
            const createBtn = document.getElementById('createRoomBtn');
            const joinBtn = document.getElementById('joinRoomBtn');
            if (createBtn) createBtn.style.display = 'none';
            if (joinBtn) joinBtn.style.display = 'none';
            
            // Show guest indicator
            if (window.showToast) {
                window.showToast(`Joined as guest: ${guestName}. Host pays for this call.`, 'info', 5000);
            }
            
            // Auto-connect to room
            if (window.connectToRoom) {
                setTimeout(() => window.connectToRoom(), 1000);
            }
        }, 500);
    }
});

