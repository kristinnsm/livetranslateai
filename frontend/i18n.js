/**
 * Simple i18n (internationalization) for UI text
 */

const translations = {
    en: {
        tagline: "Real-Time Voice Translation for Business Calls",
        createRoom: "Create Room",
        joinRoom: "Join Room",
        roomCode: "Room Code:",
        participants: "Participants",
        from: "From",
        to: "To",
        startSpeaking: "Start Speaking",
        stopTranslate: "Stop & Translate",
        original: "Original",
        translation: "Translation",
        replay: "Replay",
        replayLast: "Replay Last Translation",
        waitingForSpeech: "Waiting for speech...",
        readyToTranslate: "Ready to translate...",
        connecting: "Connecting...",
        connected: "Connected",
        recording: "Recording...",
        readyForNext: "Ready for next recording"
    },
    es: {
        tagline: "Traducción de Voz en Tiempo Real para Llamadas de Negocios",
        createRoom: "Crear Sala",
        joinRoom: "Unirse a Sala",
        roomCode: "Código de Sala:",
        participants: "Participantes",
        from: "De",
        to: "A",
        startSpeaking: "Comenzar a Hablar",
        stopTranslate: "Detener y Traducir",
        original: "Original",
        translation: "Traducción",
        replay: "Reproducir",
        replayLast: "Reproducir Última Traducción",
        waitingForSpeech: "Esperando voz...",
        readyToTranslate: "Listo para traducir...",
        connecting: "Conectando...",
        connected: "Conectado",
        recording: "Grabando...",
        readyForNext: "Listo para siguiente grabación"
    },
    fr: {
        tagline: "Traduction Vocale en Temps Réel pour Appels Professionnels",
        createRoom: "Créer une Salle",
        joinRoom: "Rejoindre une Salle",
        roomCode: "Code de Salle:",
        participants: "Participants",
        from: "De",
        to: "À",
        startSpeaking: "Commencer à Parler",
        stopTranslate: "Arrêter et Traduire",
        original: "Original",
        translation: "Traduction",
        replay: "Rejouer",
        replayLast: "Rejouer Dernière Traduction",
        waitingForSpeech: "En attente de parole...",
        readyToTranslate: "Prêt à traduire...",
        connecting: "Connexion...",
        connected: "Connecté",
        recording: "Enregistrement...",
        readyForNext: "Prêt pour le suivant"
    },
    de: {
        tagline: "Echtzeit-Sprachübersetzung für Geschäftsanrufe",
        createRoom: "Raum Erstellen",
        joinRoom: "Raum Beitreten",
        roomCode: "Raumcode:",
        participants: "Teilnehmer",
        from: "Von",
        to: "Zu",
        startSpeaking: "Sprechen Beginnen",
        stopTranslate: "Stoppen & Übersetzen",
        original: "Original",
        translation: "Übersetzung",
        replay: "Wiedergeben",
        replayLast: "Letzte Übersetzung Wiedergeben",
        waitingForSpeech: "Warten auf Sprache...",
        readyToTranslate: "Bereit zum Übersetzen...",
        connecting: "Verbinden...",
        connected: "Verbunden",
        recording: "Aufnahme...",
        readyForNext: "Bereit für nächste Aufnahme"
    },
    zh: {
        tagline: "商务通话实时语音翻译",
        createRoom: "创建房间",
        joinRoom: "加入房间",
        roomCode: "房间代码：",
        participants: "参与者",
        from: "从",
        to: "到",
        startSpeaking: "开始说话",
        stopTranslate: "停止并翻译",
        original: "原文",
        translation: "翻译",
        replay: "重播",
        replayLast: "重播最后翻译",
        waitingForSpeech: "等待语音...",
        readyToTranslate: "准备翻译...",
        connecting: "连接中...",
        connected: "已连接",
        recording: "录音中...",
        readyForNext: "准备下一次录音"
    },
    ar: {
        tagline: "ترجمة صوتية فورية لمكالمات الأعمال",
        createRoom: "إنشاء غرفة",
        joinRoom: "الانضمام إلى غرفة",
        roomCode: "رمز الغرفة:",
        participants: "المشاركون",
        from: "من",
        to: "إلى",
        startSpeaking: "ابدأ الحديث",
        stopTranslate: "إيقاف والترجمة",
        original: "الأصلي",
        translation: "الترجمة",
        replay: "إعادة",
        replayLast: "إعادة آخر ترجمة",
        waitingForSpeech: "في انتظار الكلام...",
        readyToTranslate: "جاهز للترجمة...",
        connecting: "جاري الاتصال...",
        connected: "متصل",
        recording: "جاري التسجيل...",
        readyForNext: "جاهز للتسجيل التالي"
    }
};

// Simple i18n function
function t(key, lang) {
    const userLang = lang || localStorage.getItem('uiLanguage') || 'en';
    return translations[userLang]?.[key] || translations.en[key] || key;
}

// Update all UI text elements
function updateUILanguage(lang) {
    localStorage.setItem('uiLanguage', lang);
    
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translatedText = t(key, lang);
        
        // Check if element has children (like buttons with icons)
        if (element.children.length > 0) {
            // Find text nodes and update them
            Array.from(element.childNodes).forEach(node => {
                if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                    node.textContent = translatedText;
                }
            });
        } else {
            element.textContent = translatedText;
        }
    });
    
    // Update document direction for RTL languages
    if (lang === 'ar') {
        document.documentElement.setAttribute('dir', 'rtl');
    } else {
        document.documentElement.setAttribute('dir', 'ltr');
    }
    
    console.log(`🌍 UI language changed to: ${lang}`);
}

// Export for use in app.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { t, updateUILanguage, translations };
}

