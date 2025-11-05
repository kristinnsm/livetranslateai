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
    },
    ru: {
        tagline: "Голосовой перевод в реальном времени для деловых звонков",
        createRoom: "Создать Комнату",
        joinRoom: "Присоединиться",
        roomCode: "Код комнаты:",
        participants: "Участники",
        from: "От",
        to: "К",
        startSpeaking: "Начать Говорить",
        stopTranslate: "Стоп и Перевести",
        original: "Оригинал",
        translation: "Перевод",
        replay: "Повтор",
        replayLast: "Повторить Последний",
        waitingForSpeech: "Ожидание речи...",
        readyToTranslate: "Готов к переводу...",
        connecting: "Подключение...",
        connected: "Подключено",
        recording: "Запись...",
        readyForNext: "Готов к следующей записи"
    },
    ja: {
        tagline: "ビジネス通話用リアルタイム音声翻訳",
        createRoom: "ルーム作成",
        joinRoom: "参加",
        roomCode: "ルームコード：",
        participants: "参加者",
        from: "から",
        to: "へ",
        startSpeaking: "話す",
        stopTranslate: "停止して翻訳",
        original: "原文",
        translation: "翻訳",
        replay: "再生",
        replayLast: "最後の翻訳を再生",
        waitingForSpeech: "音声待機中...",
        readyToTranslate: "翻訳準備完了...",
        connecting: "接続中...",
        connected: "接続済み",
        recording: "録音中...",
        readyForNext: "次の録音準備完了"
    },
    ko: {
        tagline: "비즈니스 통화를 위한 실시간 음성 번역",
        createRoom: "방 만들기",
        joinRoom: "참여하기",
        roomCode: "방 코드:",
        participants: "참가자",
        from: "에서",
        to: "로",
        startSpeaking: "말하기 시작",
        stopTranslate: "중지 및 번역",
        original: "원문",
        translation: "번역",
        replay: "재생",
        replayLast: "마지막 번역 재생",
        waitingForSpeech: "음성 대기 중...",
        readyToTranslate: "번역 준비 완료...",
        connecting: "연결 중...",
        connected: "연결됨",
        recording: "녹음 중...",
        readyForNext: "다음 녹음 준비"
    },
    pt: {
        tagline: "Tradução de Voz em Tempo Real para Chamadas Comerciais",
        createRoom: "Criar Sala",
        joinRoom: "Entrar na Sala",
        roomCode: "Código da Sala:",
        participants: "Participantes",
        from: "De",
        to: "Para",
        startSpeaking: "Começar a Falar",
        stopTranslate: "Parar e Traduzir",
        original: "Original",
        translation: "Tradução",
        replay: "Repetir",
        replayLast: "Repetir Última",
        waitingForSpeech: "Aguardando fala...",
        readyToTranslate: "Pronto para traduzir...",
        connecting: "Conectando...",
        connected: "Conectado",
        recording: "Gravando...",
        readyForNext: "Pronto para próxima"
    },
    it: {
        tagline: "Traduzione Vocale in Tempo Reale per Chiamate Aziendali",
        createRoom: "Crea Stanza",
        joinRoom: "Unisciti",
        roomCode: "Codice Stanza:",
        participants: "Partecipanti",
        from: "Da",
        to: "A",
        startSpeaking: "Inizia a Parlare",
        stopTranslate: "Stop e Traduci",
        original: "Originale",
        translation: "Traduzione",
        replay: "Riproduci",
        replayLast: "Riproduci Ultima",
        waitingForSpeech: "In attesa di parlato...",
        readyToTranslate: "Pronto a tradurre...",
        connecting: "Connessione...",
        connected: "Connesso",
        recording: "Registrazione...",
        readyForNext: "Pronto per la prossima"
    },
    nl: {
        tagline: "Realtime Spraakvertaling voor Zakelijke Gesprekken",
        createRoom: "Kamer Maken",
        joinRoom: "Deelnemen",
        roomCode: "Kamercode:",
        participants: "Deelnemers",
        from: "Van",
        to: "Naar",
        startSpeaking: "Begin Spreken",
        stopTranslate: "Stop en Vertaal",
        original: "Origineel",
        translation: "Vertaling",
        replay: "Afspelen",
        replayLast: "Laatste Herhalen",
        waitingForSpeech: "Wachten op spraak...",
        readyToTranslate: "Klaar om te vertalen...",
        connecting: "Verbinden...",
        connected: "Verbonden",
        recording: "Opnemen...",
        readyForNext: "Klaar voor volgende"
    },
    hi: {
        tagline: "व्यावसायिक कॉल के लिए रीयल-टाइम वॉइस अनुवाद",
        createRoom: "रूम बनाएं",
        joinRoom: "शामिल हों",
        roomCode: "रूम कोड:",
        participants: "प्रतिभागी",
        from: "से",
        to: "तक",
        startSpeaking: "बोलना शुरू करें",
        stopTranslate: "रुकें और अनुवाद करें",
        original: "मूल",
        translation: "अनुवाद",
        replay: "रीप्ले",
        replayLast: "अंतिम अनुवाद रीप्ले",
        waitingForSpeech: "भाषण की प्रतीक्षा में...",
        readyToTranslate: "अनुवाद के लिए तैयार...",
        connecting: "कनेक्ट हो रहा है...",
        connected: "कनेक्टेड",
        recording: "रिकॉर्डिंग...",
        readyForNext: "अगले के लिए तैयार"
    },
    tr: {
        tagline: "İş Görüşmeleri için Gerçek Zamanlı Sesli Çeviri",
        createRoom: "Oda Oluştur",
        joinRoom: "Katıl",
        roomCode: "Oda Kodu:",
        participants: "Katılımcılar",
        from: "Den",
        to: "E",
        startSpeaking: "Konuşmaya Başla",
        stopTranslate: "Durdur ve Çevir",
        original: "Orijinal",
        translation: "Çeviri",
        replay: "Tekrar",
        replayLast: "Son Çeviriyi Tekrarla",
        waitingForSpeech: "Konuşma bekleniyor...",
        readyToTranslate: "Çeviriye hazır...",
        connecting: "Bağlanıyor...",
        connected: "Bağlandı",
        recording: "Kaydediliyor...",
        readyForNext: "Sonraki için hazır"
    },
    vi: {
        tagline: "Dịch Giọng Nói Thời Gian Thực cho Cuộc Gọi Kinh Doanh",
        createRoom: "Tạo Phòng",
        joinRoom: "Tham Gia",
        roomCode: "Mã Phòng:",
        participants: "Người tham gia",
        from: "Từ",
        to: "Đến",
        startSpeaking: "Bắt Đầu Nói",
        stopTranslate: "Dừng và Dịch",
        original: "Gốc",
        translation: "Dịch",
        replay: "Phát Lại",
        replayLast: "Phát Lại Lần Cuối",
        waitingForSpeech: "Đang chờ lời nói...",
        readyToTranslate: "Sẵn sàng dịch...",
        connecting: "Đang kết nối...",
        connected: "Đã kết nối",
        recording: "Đang ghi...",
        readyForNext: "Sẵn sàng cho lần tiếp theo"
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

