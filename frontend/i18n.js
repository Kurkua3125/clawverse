/**
 * Clawverse i18n — Internationalization module
 * Supports: en, ja, ko, zh-CN, zh-TW, hi, pt-BR, fr
 */
(function() {
  'use strict';

  const SUPPORTED_LANGS = ['en', 'ja', 'ko', 'zh-CN', 'zh-TW', 'hi', 'pt-BR', 'fr'];
  const DEFAULT_LANG = 'en';
  const STORAGE_KEY = 'clawverse-lang';

  const translations = {
    // ── Page titles ──
    'page.title.island': {
      en: '🦞 Clawverse — Universe of Claws',
      ja: '🦞 クローバース — 爪の宇宙',
      ko: '🦞 클로버스 — 집게의 우주',
      'zh-CN': '🦞 蟹爪宇宙 — Universe of Claws',
      'zh-TW': '🦞 蟹爪宇宙 — Universe of Claws',
      hi: '🦞 क्लॉवर्स — पंजों का ब्रह्मांड',
      'pt-BR': '🦞 Clawverse — Universo das Garras',
      fr: '🦞 Clawverse — Univers des Pinces'
    },
    'page.title.lobby': {
      en: '🌏 Clawverse — Universe of Claws',
      ja: '🌏 クローバース — 爪の宇宙',
      ko: '🌏 클로버스 — 집게의 우주',
      'zh-CN': '🌏 蟹爪宇宙 — Universe of Claws',
      'zh-TW': '🌏 蟹爪宇宙 — Universe of Claws',
      hi: '🌏 क्लॉवर्स — पंजों का ब्रह्मांड',
      'pt-BR': '🌏 Clawverse — Universo das Garras',
      fr: '🌏 Clawverse — Univers des Pinces'
    },
    'page.title.map': {
      en: '🗺️ Clawverse World Map',
      ja: '🗺️ クローバース ワールドマップ',
      ko: '🗺️ 클로버스 월드맵',
      'zh-CN': '🗺️ 蟹爪宇宙 世界地图',
      'zh-TW': '🗺️ 蟹爪宇宙 世界地圖',
      hi: '🗺️ क्लॉवर्स विश्व मानचित्र',
      'pt-BR': '🗺️ Mapa Mundial Clawverse',
      fr: '🗺️ Carte du Monde Clawverse'
    },

    // ── Nav / Toolbar buttons ──
    'nav.build': {
      en: '🛠 Build', ja: '🛠 建設', ko: '🛠 건설', 'zh-CN': '🛠 建造', 'zh-TW': '🛠 建造',
      hi: '🛠 निर्माण', 'pt-BR': '🛠 Construir', fr: '🛠 Construire'
    },
    'nav.explore': {
      en: '👁 Explore', ja: '👁 探索', ko: '👁 탐험', 'zh-CN': '👁 探索', 'zh-TW': '👁 探索',
      hi: '👁 अन्वेषण', 'pt-BR': '👁 Explorar', fr: '👁 Explorer'
    },
    'nav.farm': {
      en: '🌾 Farm', ja: '🌾 農場', ko: '🌾 농장', 'zh-CN': '🌾 农场', 'zh-TW': '🌾 農場',
      hi: '🌾 खेत', 'pt-BR': '🌾 Fazenda', fr: '🌾 Ferme'
    },
    'nav.shop': {
      en: '🏪 Shop', ja: '🏪 ショップ', ko: '🏪 상점', 'zh-CN': '🏪 商店', 'zh-TW': '🏪 商店',
      hi: '🏪 दुकान', 'pt-BR': '🏪 Loja', fr: '🏪 Boutique'
    },
    'nav.bag': {
      en: '📦 Bag', ja: '📦 バッグ', ko: '📦 가방', 'zh-CN': '📦 背包', 'zh-TW': '📦 背包',
      hi: '📦 बैग', 'pt-BR': '📦 Mochila', fr: '📦 Sac'
    },
    'nav.land': {
      en: '🗺️ Land', ja: '🗺️ 土地', ko: '🗺️ 토지', 'zh-CN': '🗺️ 土地', 'zh-TW': '🗺️ 土地',
      hi: '🗺️ भूमि', 'pt-BR': '🗺️ Terreno', fr: '🗺️ Terrain'
    },
    'nav.lobby': {
      en: '← Lobby', ja: '← ロビー', ko: '← 로비', 'zh-CN': '← 大厅', 'zh-TW': '← 大廳',
      hi: '← लॉबी', 'pt-BR': '← Lobby', fr: '← Lobby'
    },
    'nav.lobby.icon': {
      en: '🏠 Lobby', ja: '🏠 ロビー', ko: '🏠 로비', 'zh-CN': '🏠 大厅', 'zh-TW': '🏠 大廳',
      hi: '🏠 लॉबी', 'pt-BR': '🏠 Lobby', fr: '🏠 Lobby'
    },
    'nav.login': {
      en: 'Log in', ja: 'ログイン', ko: '로그인', 'zh-CN': '登录', 'zh-TW': '登入',
      hi: 'लॉग इन', 'pt-BR': 'Entrar', fr: 'Connexion'
    },
    'nav.signup': {
      en: '🦞 Sign Up / Log In', ja: '🦞 登録 / ログイン', ko: '🦞 가입 / 로그인',
      'zh-CN': '🦞 注册 / 登录', 'zh-TW': '🦞 註冊 / 登入',
      hi: '🦞 साइन अप / लॉग इन', 'pt-BR': '🦞 Cadastrar / Entrar', fr: '🦞 Inscription / Connexion'
    },

    // ── Visitor Welcome overlay ──
    'visitor.welcome': {
      en: 'Welcome, explorer!', ja: 'ようこそ、探検家！', ko: '환영합니다, 탐험가!',
      'zh-CN': '欢迎，探险家！', 'zh-TW': '歡迎，探險家！',
      hi: 'स्वागत है, अन्वेषक!', 'pt-BR': 'Bem-vindo, explorador!', fr: 'Bienvenue, explorateur !'
    },
    'visitor.start_exploring': {
      en: '🎮 Start Exploring', ja: '🎮 探索を始める', ko: '🎮 탐험 시작',
      'zh-CN': '🎮 开始探索', 'zh-TW': '🎮 開始探索',
      hi: '🎮 अन्वेषण शुरू करें', 'pt-BR': '🎮 Começar a Explorar', fr: '🎮 Commencer l\'Exploration'
    },
    'visitor.guestbook': {
      en: '📝 Guestbook', ja: '📝 ゲストブック', ko: '📝 방명록',
      'zh-CN': '📝 留言簿', 'zh-TW': '📝 留言簿',
      hi: '📝 अतिथि पुस्तिका', 'pt-BR': '📝 Livro de Visitas', fr: '📝 Livre d\'Or'
    },
    'visitor.create_own': {
      en: '🏝️ Create Your Own', ja: '🏝️ 自分の島を作る', ko: '🏝️ 나만의 섬 만들기',
      'zh-CN': '🏝️ 创建你的岛屿', 'zh-TW': '🏝️ 建立你的島嶼',
      hi: '🏝️ अपना बनाएं', 'pt-BR': '🏝️ Crie a Sua', fr: '🏝️ Créez la Vôtre'
    },
    'visitor.browse_islands': {
      en: 'Browse islands', ja: '島を閲覧', ko: '섬 둘러보기',
      'zh-CN': '浏览岛屿', 'zh-TW': '瀏覽島嶼',
      hi: 'द्वीप ब्राउज़ करें', 'pt-BR': 'Explorar ilhas', fr: 'Parcourir les îles'
    },

    // ── Lobby / Hero ──
    'lobby.hero.subtitle': {
      en: 'Build your pixel island. Visit friends. Collect everything. 🦞',
      ja: 'ピクセルの島を作ろう。友達を訪ねよう。すべてを集めよう。🦞',
      ko: '픽셀 섬을 만드세요. 친구를 방문하세요. 모든 것을 수집하세요. 🦞',
      'zh-CN': '建造你的像素岛。访问朋友。收集一切。🦞',
      'zh-TW': '建造你的像素島。拜訪朋友。收集一切。🦞',
      hi: 'अपना पिक्सेल द्वीप बनाएं। दोस्तों से मिलें। सब कुछ इकट्ठा करें। 🦞',
      'pt-BR': 'Construa sua ilha de pixels. Visite amigos. Colete tudo. 🦞',
      fr: 'Construisez votre île en pixels. Visitez vos amis. Collectionnez tout. 🦞'
    },
    'lobby.create_island': {
      en: '🦞 Create Your Island — It\'s Free!',
      ja: '🦞 島を作ろう — 無料です！',
      ko: '🦞 나만의 섬을 만드세요 — 무료!',
      'zh-CN': '🦞 创建你的岛屿 — 完全免费！',
      'zh-TW': '🦞 建立你的島嶼 — 完全免費！',
      hi: '🦞 अपना द्वीप बनाएं — यह मुफ़्त है!',
      'pt-BR': '🦞 Crie Sua Ilha — É Grátis!',
      fr: '🦞 Créez Votre Île — C\'est Gratuit !'
    },
    'lobby.create_island_short': {
      en: '🦞 Create Your Island',
      ja: '🦞 島を作ろう',
      ko: '🦞 나만의 섬 만들기',
      'zh-CN': '🦞 创建你的岛屿',
      'zh-TW': '🦞 建立你的島嶼',
      hi: '🦞 अपना द्वीप बनाएं',
      'pt-BR': '🦞 Crie Sua Ilha',
      fr: '🦞 Créez Votre Île'
    },
    'lobby.view_all_islands': {
      en: '🌏 View all islands',
      ja: '🌏 すべての島を見る',
      ko: '🌏 모든 섬 보기',
      'zh-CN': '🌏 查看所有岛屿',
      'zh-TW': '🌏 查看所有島嶼',
      hi: '🌏 सभी द्वीप देखें',
      'pt-BR': '🌏 Ver todas as ilhas',
      fr: '🌏 Voir toutes les îles'
    },

    // ── Section titles ──
    'section.featured': {
      en: '⭐ Featured', ja: '⭐ 注目', ko: '⭐ 추천',
      'zh-CN': '⭐ 精选', 'zh-TW': '⭐ 精選',
      hi: '⭐ विशेष', 'pt-BR': '⭐ Destaque', fr: '⭐ En Vedette'
    },
    'section.all_islands': {
      en: '🏝️ All Islands', ja: '🏝️ すべての島', ko: '🏝️ 모든 섬',
      'zh-CN': '🏝️ 所有岛屿', 'zh-TW': '🏝️ 所有島嶼',
      hi: '🏝️ सभी द्वीप', 'pt-BR': '🏝️ Todas as Ilhas', fr: '🏝️ Toutes les Îles'
    },
    'section.explore_islands': {
      en: '🏝️ Explore Islands', ja: '🏝️ 島を探索', ko: '🏝️ 섬 탐색',
      'zh-CN': '🏝️ 探索岛屿', 'zh-TW': '🏝️ 探索島嶼',
      hi: '🏝️ द्वीप खोजें', 'pt-BR': '🏝️ Explorar Ilhas', fr: '🏝️ Explorer les Îles'
    },
    'section.new_islands': {
      en: '🆕 New Islands', ja: '🆕 新しい島', ko: '🆕 새로운 섬',
      'zh-CN': '🆕 新岛屿', 'zh-TW': '🆕 新島嶼',
      hi: '🆕 नए द्वीप', 'pt-BR': '🆕 Novas Ilhas', fr: '🆕 Nouvelles Îles'
    },
    'section.popular_islands': {
      en: '🔥 Popular', ja: '🔥 人気の島', ko: '🔥 인기 섬',
      'zh-CN': '🔥 热门岛屿', 'zh-TW': '🔥 熱門島嶼',
      hi: '🔥 लोकप्रिय', 'pt-BR': '🔥 Populares', fr: '🔥 Populaires'
    },
    'section.recent_activity': {
      en: '⚡ Recent Activity', ja: '⚡ 最近のアクティビティ', ko: '⚡ 최근 활동',
      'zh-CN': '⚡ 最近活动', 'zh-TW': '⚡ 最近活動',
      hi: '⚡ हाल की गतिविधि', 'pt-BR': '⚡ Atividade Recente', fr: '⚡ Activité Récente'
    },
    'section.leaderboard': {
      en: '🏆 Leaderboard', ja: '🏆 ランキング', ko: '🏆 리더보드',
      'zh-CN': '🏆 排行榜', 'zh-TW': '🏆 排行榜',
      hi: '🏆 लीडरबोर्ड', 'pt-BR': '🏆 Classificação', fr: '🏆 Classement'
    },

    // ── Sort / Filter buttons ──
    'sort.popular': {
      en: '🔥 Popular', ja: '🔥 人気', ko: '🔥 인기',
      'zh-CN': '🔥 热门', 'zh-TW': '🔥 熱門',
      hi: '🔥 लोकप्रिय', 'pt-BR': '🔥 Popular', fr: '🔥 Populaire'
    },
    'sort.recent': {
      en: '🕐 Recent', ja: '🕐 最新', ko: '🕐 최신',
      'zh-CN': '🕐 最新', 'zh-TW': '🕐 最新',
      hi: '🕐 हाल ही', 'pt-BR': '🕐 Recente', fr: '🕐 Récent'
    },
    'sort.random': {
      en: '🎲 Random', ja: '🎲 ランダム', ko: '🎲 랜덤',
      'zh-CN': '🎲 随机', 'zh-TW': '🎲 隨機',
      hi: '🎲 यादृच्छिक', 'pt-BR': '🎲 Aleatório', fr: '🎲 Aléatoire'
    },
    'sort.trending': {
      en: '📈 Trending', ja: '📈 トレンド', ko: '📈 트렌딩',
      'zh-CN': '📈 趋势', 'zh-TW': '📈 趨勢',
      hi: '📈 ट्रेंडिंग', 'pt-BR': '📈 Em Alta', fr: '📈 Tendance'
    },
    'filter.all': {
      en: 'All', ja: 'すべて', ko: '전체',
      'zh-CN': '全部', 'zh-TW': '全部',
      hi: 'सभी', 'pt-BR': 'Todos', fr: 'Tous'
    },
    'filter.farm': {
      en: '🌾 Farm', ja: '🌾 農場', ko: '🌾 농장',
      'zh-CN': '🌾 农场', 'zh-TW': '🌾 農場',
      hi: '🌾 खेत', 'pt-BR': '🌾 Fazenda', fr: '🌾 Ferme'
    },
    'filter.fish': {
      en: '🐟 Fish', ja: '🐟 釣り', ko: '🐟 낚시',
      'zh-CN': '🐟 渔场', 'zh-TW': '🐟 漁場',
      hi: '🐟 मछली', 'pt-BR': '🐟 Pesca', fr: '🐟 Pêche'
    },
    'filter.mine': {
      en: '⛏️ Mining', ja: '⛏️ 鉱山', ko: '⛏️ 광산',
      'zh-CN': '⛏️ 矿山', 'zh-TW': '⛏️ 礦山',
      hi: '⛏️ खदान', 'pt-BR': '⛏️ Mina', fr: '⛏️ Mine'
    },
    'filter.forest': {
      en: '🌲 Forest', ja: '🌲 森林', ko: '🌲 숲',
      'zh-CN': '🌲 森林', 'zh-TW': '🌲 森林',
      hi: '🌲 जंगल', 'pt-BR': '🌲 Floresta', fr: '🌲 Forêt'
    },
    'filter.label': {
      en: 'Filter', ja: 'フィルター', ko: '필터',
      'zh-CN': '筛选', 'zh-TW': '篩選',
      hi: 'फ़िल्टर', 'pt-BR': 'Filtro', fr: 'Filtre'
    },
    'filter.sort': {
      en: 'Sort:', ja: '並び替え:', ko: '정렬:',
      'zh-CN': '排序:', 'zh-TW': '排序:',
      hi: 'क्रमबद्ध:', 'pt-BR': 'Ordenar:', fr: 'Trier :'
    },
    'filter.type': {
      en: 'Type:', ja: 'タイプ:', ko: '유형:',
      'zh-CN': '类型:', 'zh-TW': '類型:',
      hi: 'प्रकार:', 'pt-BR': 'Tipo:', fr: 'Type :'
    },
    'filter.all_types': {
      en: 'All Types', ja: 'すべてのタイプ', ko: '모든 유형',
      'zh-CN': '所有类型', 'zh-TW': '所有類型',
      hi: 'सभी प्रकार', 'pt-BR': 'Todos os Tipos', fr: 'Tous les Types'
    },
    'filter.showing': {
      en: 'Showing:', ja: '表示中:', ko: '표시:',
      'zh-CN': '当前显示:', 'zh-TW': '目前顯示:',
      hi: 'दिखा रहा:', 'pt-BR': 'Exibindo:', fr: 'Affichage :'
    },

    // ── Search ──
    'search.placeholder': {
      en: 'Search by name, creator, or type...',
      ja: '名前、作成者、またはタイプで検索...',
      ko: '이름, 제작자 또는 유형으로 검색...',
      'zh-CN': '按名称、创建者或类型搜索...',
      'zh-TW': '按名稱、建立者或類型搜尋...',
      hi: 'नाम, निर्माता, या प्रकार से खोजें...',
      'pt-BR': 'Buscar por nome, criador ou tipo...',
      fr: 'Rechercher par nom, créateur ou type...'
    },

    // ── Stats ──
    'stats.items': {
      en: 'items', ja: 'アイテム', ko: '아이템',
      'zh-CN': '物品', 'zh-TW': '物品',
      hi: 'आइटम', 'pt-BR': 'itens', fr: 'objets'
    },
    'stats.visits': {
      en: 'visits', ja: '訪問', ko: '방문',
      'zh-CN': '访问', 'zh-TW': '訪問',
      hi: 'विज़िट', 'pt-BR': 'visitas', fr: 'visites'
    },
    'stats.online': {
      en: 'online', ja: 'オンライン', ko: '온라인',
      'zh-CN': '在线', 'zh-TW': '在線',
      hi: 'ऑनलाइन', 'pt-BR': 'online', fr: 'en ligne'
    },
    'stats.islands': {
      en: 'islands', ja: '島', ko: '섬',
      'zh-CN': '岛屿', 'zh-TW': '島嶼',
      hi: 'द्वीप', 'pt-BR': 'ilhas', fr: 'îles'
    },
    'stats.objects': {
      en: 'objects', ja: 'オブジェクト', ko: '오브젝트',
      'zh-CN': '物体', 'zh-TW': '物體',
      hi: 'वस्तुएँ', 'pt-BR': 'objetos', fr: 'objets'
    },
    'stats.level': {
      en: 'Level', ja: 'レベル', ko: '레벨',
      'zh-CN': '等级', 'zh-TW': '等級',
      hi: 'स्तर', 'pt-BR': 'Nível', fr: 'Niveau'
    },

    // ── Bag tabs ──
    'bag.resources': {
      en: '📦 Resources', ja: '📦 資源', ko: '📦 자원',
      'zh-CN': '📦 资源', 'zh-TW': '📦 資源',
      hi: '📦 संसाधन', 'pt-BR': '📦 Recursos', fr: '📦 Ressources'
    },
    'bag.items': {
      en: '🎒 Items', ja: '🎒 アイテム', ko: '🎒 아이템',
      'zh-CN': '🎒 物品', 'zh-TW': '🎒 物品',
      hi: '🎒 आइटम', 'pt-BR': '🎒 Itens', fr: '🎒 Objets'
    },
    'bag.craft': {
      en: '🔨 Craft', ja: '🔨 クラフト', ko: '🔨 제작',
      'zh-CN': '🔨 制作', 'zh-TW': '🔨 製作',
      hi: '🔨 क्राफ्ट', 'pt-BR': '🔨 Criar', fr: '🔨 Artisanat'
    },

    // ── Shop tabs ──
    'shop.build': {
      en: '🛠 Build', ja: '🛠 建設', ko: '🛠 건설',
      'zh-CN': '🛠 建造', 'zh-TW': '🛠 建造',
      hi: '🛠 निर्माण', 'pt-BR': '🛠 Construir', fr: '🛠 Construire'
    },
    'shop.market': {
      en: '📤 Market', ja: '📤 マーケット', ko: '📤 마켓',
      'zh-CN': '📤 市场', 'zh-TW': '📤 市場',
      hi: '📤 बाज़ार', 'pt-BR': '📤 Mercado', fr: '📤 Marché'
    },
    'shop.prices': {
      en: '📊 Prices', ja: '📊 価格', ko: '📊 가격',
      'zh-CN': '📊 价格', 'zh-TW': '📊 價格',
      hi: '📊 कीमतें', 'pt-BR': '📊 Preços', fr: '📊 Prix'
    },

    // ── Farm UI ──
    'farm.panel_title': {
      en: '🌱 Farm & Market', ja: '🌱 農場＆マーケット', ko: '🌱 농장 & 마켓',
      'zh-CN': '🌱 农场与市场', 'zh-TW': '🌱 農場與市場',
      hi: '🌱 खेत और बाज़ार', 'pt-BR': '🌱 Fazenda & Mercado', fr: '🌱 Ferme & Marché'
    },
    'farm.crops': {
      en: '🌱 Crops', ja: '🌱 作物', ko: '🌱 작물',
      'zh-CN': '🌱 作物', 'zh-TW': '🌱 作物',
      hi: '🌱 फसलें', 'pt-BR': '🌱 Colheitas', fr: '🌱 Cultures'
    },
    'farm.market': {
      en: '📈 Market', ja: '📈 マーケット', ko: '📈 마켓',
      'zh-CN': '📈 市场', 'zh-TW': '📈 市場',
      hi: '📈 बाज़ार', 'pt-BR': '📈 Mercado', fr: '📈 Marché'
    },
    'farm.feed': {
      en: '📜 Feed', ja: '📜 フィード', ko: '📜 피드',
      'zh-CN': '📜 动态', 'zh-TW': '📜 動態',
      hi: '📜 फ़ीड', 'pt-BR': '📜 Feed', fr: '📜 Flux'
    },
    'farm.plant': {
      en: 'Plant', ja: '植える', ko: '심기',
      'zh-CN': '种植', 'zh-TW': '種植',
      hi: 'बोएं', 'pt-BR': 'Plantar', fr: 'Planter'
    },
    'farm.harvest': {
      en: 'Harvest', ja: '収穫', ko: '수확',
      'zh-CN': '收获', 'zh-TW': '收穫',
      hi: 'फसल काटें', 'pt-BR': 'Colher', fr: 'Récolter'
    },
    'farm.water': {
      en: 'Water', ja: '水やり', ko: '물주기',
      'zh-CN': '浇水', 'zh-TW': '澆水',
      hi: 'पानी दें', 'pt-BR': 'Regar', fr: 'Arroser'
    },
    'farm.stats': {
      en: '📊 Stats', ja: '📊 統計', ko: '📊 통계',
      'zh-CN': '📊 统计', 'zh-TW': '📊 統計',
      hi: '📊 आँकड़े', 'pt-BR': '📊 Estatísticas', fr: '📊 Statistiques'
    },
    'farm.exit': {
      en: '✕ Exit', ja: '✕ 退出', ko: '✕ 나가기',
      'zh-CN': '✕ 退出', 'zh-TW': '✕ 退出',
      hi: '✕ बाहर', 'pt-BR': '✕ Sair', fr: '✕ Quitter'
    },
    'farm.plant_crops': {
      en: 'Plant crops on the farm:', ja: '農場に作物を植えましょう:', ko: '농장에 작물을 심으세요:',
      'zh-CN': '在农场种植作物:', 'zh-TW': '在農場種植作物:',
      hi: 'खेत पर फसलें लगाएं:', 'pt-BR': 'Plante colheitas na fazenda:', fr: 'Plantez des cultures sur la ferme :'
    },

    // ── More menu items ──
    'menu.all_islands': {
      en: '🌏 All Islands', ja: '🌏 すべての島', ko: '🌏 모든 섬',
      'zh-CN': '🌏 所有岛屿', 'zh-TW': '🌏 所有島嶼',
      hi: '🌏 सभी द्वीप', 'pt-BR': '🌏 Todas as Ilhas', fr: '🌏 Toutes les Îles'
    },
    'menu.guestbook': {
      en: '📝 Guestbook', ja: '📝 ゲストブック', ko: '📝 방명록',
      'zh-CN': '📝 留言簿', 'zh-TW': '📝 留言簿',
      hi: '📝 अतिथि पुस्तिका', 'pt-BR': '📝 Livro de Visitas', fr: '📝 Livre d\'Or'
    },
    'menu.share': {
      en: '📤 Share', ja: '📤 共有', ko: '📤 공유',
      'zh-CN': '📤 分享', 'zh-TW': '📤 分享',
      hi: '📤 शेयर', 'pt-BR': '📤 Compartilhar', fr: '📤 Partager'
    },
    'menu.leaderboard': {
      en: '🏆 Leaderboard', ja: '🏆 ランキング', ko: '🏆 리더보드',
      'zh-CN': '🏆 排行榜', 'zh-TW': '🏆 排行榜',
      hi: '🏆 लीडरबोर्ड', 'pt-BR': '🏆 Classificação', fr: '🏆 Classement'
    },
    'menu.help': {
      en: '❓ Help', ja: '❓ ヘルプ', ko: '❓ 도움말',
      'zh-CN': '❓ 帮助', 'zh-TW': '❓ 幫助',
      hi: '❓ सहायता', 'pt-BR': '❓ Ajuda', fr: '❓ Aide'
    },
    'menu.achievements': {
      en: '🏅 Achievements', ja: '🏅 実績', ko: '🏅 업적',
      'zh-CN': '🏅 成就', 'zh-TW': '🏅 成就',
      hi: '🏅 उपलब्धियाँ', 'pt-BR': '🏅 Conquistas', fr: '🏅 Succès'
    },
    'menu.farm_panel': {
      en: '🌱 Farm Panel', ja: '🌱 農場パネル', ko: '🌱 농장 패널',
      'zh-CN': '🌱 农场面板', 'zh-TW': '🌱 農場面板',
      hi: '🌱 खेत पैनल', 'pt-BR': '🌱 Painel da Fazenda', fr: '🌱 Panneau de Ferme'
    },
    'menu.snapshot': {
      en: '📸 Snapshot', ja: '📸 スナップショット', ko: '📸 스냅샷',
      'zh-CN': '📸 快照', 'zh-TW': '📸 快照',
      hi: '📸 स्नैपशॉट', 'pt-BR': '📸 Captura', fr: '📸 Instantané'
    },
    'menu.statistics': {
      en: '📊 Statistics', ja: '📊 統計', ko: '📊 통계',
      'zh-CN': '📊 统计', 'zh-TW': '📊 統計',
      hi: '📊 आँकड़े', 'pt-BR': '📊 Estatísticas', fr: '📊 Statistiques'
    },
    'menu.customize': {
      en: '🎨 Customize', ja: '🎨 カスタマイズ', ko: '🎨 커스터마이즈',
      'zh-CN': '🎨 自定义', 'zh-TW': '🎨 自訂',
      hi: '🎨 अनुकूलित', 'pt-BR': '🎨 Personalizar', fr: '🎨 Personnaliser'
    },
    'menu.ai_layout': {
      en: '🤖 AI Layout', ja: '🤖 AIレイアウト', ko: '🤖 AI 레이아웃',
      'zh-CN': '🤖 AI布局', 'zh-TW': '🤖 AI佈局',
      hi: '🤖 AI लेआउट', 'pt-BR': '🤖 Layout AI', fr: '🤖 Mise en Page IA'
    },
    'menu.story': {
      en: '📖 Story', ja: '📖 ストーリー', ko: '📖 스토리',
      'zh-CN': '📖 故事', 'zh-TW': '📖 故事',
      hi: '📖 कहानी', 'pt-BR': '📖 História', fr: '📖 Histoire'
    },
    'menu.messages': {
      en: '💬 Messages', ja: '💬 メッセージ', ko: '💬 메시지',
      'zh-CN': '💬 消息', 'zh-TW': '💬 訊息',
      hi: '💬 संदेश', 'pt-BR': '💬 Mensagens', fr: '💬 Messages'
    },
    'menu.options': {
      en: 'OPTIONS', ja: 'オプション', ko: '옵션',
      'zh-CN': '选项', 'zh-TW': '選項',
      hi: 'विकल्प', 'pt-BR': 'OPÇÕES', fr: 'OPTIONS'
    },

    // ── Explore panel ──
    'explore.more_islands': {
      en: '🏝️ Explore More Islands', ja: '🏝️ もっと島を探索', ko: '🏝️ 더 많은 섬 탐험',
      'zh-CN': '🏝️ 探索更多岛屿', 'zh-TW': '🏝️ 探索更多島嶼',
      hi: '🏝️ और द्वीप खोजें', 'pt-BR': '🏝️ Explorar Mais Ilhas', fr: '🏝️ Explorer Plus d\'Îles'
    },
    'explore.islands': {
      en: '🏝️ Explore Islands', ja: '🏝️ 島を探索', ko: '🏝️ 섬 탐험',
      'zh-CN': '🏝️ 探索岛屿', 'zh-TW': '🏝️ 探索島嶼',
      hi: '🏝️ द्वीप खोजें', 'pt-BR': '🏝️ Explorar Ilhas', fr: '🏝️ Explorer les Îles'
    },
    'explore.view_all': {
      en: 'View All →', ja: 'すべて見る →', ko: '모두 보기 →',
      'zh-CN': '查看全部 →', 'zh-TW': '查看全部 →',
      hi: 'सभी देखें →', 'pt-BR': 'Ver Todos →', fr: 'Voir Tout →'
    },
    'explore.click_to_explore': {
      en: ' · Click to explore ▲', ja: ' · クリックして探索 ▲', ko: ' · 클릭하여 탐험 ▲',
      'zh-CN': ' · 点击探索 ▲', 'zh-TW': ' · 點擊探索 ▲',
      hi: ' · अन्वेषण के लिए क्लिक करें ▲', 'pt-BR': ' · Clique para explorar ▲', fr: ' · Cliquer pour explorer ▲'
    },

    // ── Map page ──
    'map.title': {
      en: '🗺️ Clawverse World Map', ja: '🗺️ クローバース ワールドマップ', ko: '🗺️ 클로버스 월드맵',
      'zh-CN': '🗺️ 蟹爪宇宙 世界地图', 'zh-TW': '🗺️ 蟹爪宇宙 世界地圖',
      hi: '🗺️ क्लॉवर्स विश्व मानचित्र', 'pt-BR': '🗺️ Mapa Mundial Clawverse', fr: '🗺️ Carte du Monde Clawverse'
    },
    'map.explore_all': {
      en: 'Explore all registered islands', ja: '登録されたすべての島を探索', ko: '등록된 모든 섬을 탐험하세요',
      'zh-CN': '探索所有已注册的岛屿', 'zh-TW': '探索所有已註冊的島嶼',
      hi: 'सभी पंजीकृत द्वीपों का अन्वेषण करें', 'pt-BR': 'Explore todas as ilhas registradas', fr: 'Explorez toutes les îles enregistrées'
    },
    'map.back': {
      en: '← Back to My Island', ja: '← 自分の島に戻る', ko: '← 내 섬으로 돌아가기',
      'zh-CN': '← 返回我的岛屿', 'zh-TW': '← 返回我的島嶼',
      hi: '← मेरे द्वीप पर वापस', 'pt-BR': '← Voltar para Minha Ilha', fr: '← Retour à Mon Île'
    },
    'map.islands_count': {
      en: '🌏 Islands:', ja: '🌏 島数:', ko: '🌏 섬:',
      'zh-CN': '🌏 岛屿:', 'zh-TW': '🌏 島嶼:',
      hi: '🌏 द्वीप:', 'pt-BR': '🌏 Ilhas:', fr: '🌏 Îles :'
    },
    'map.total_objects': {
      en: '🦞 Total Objects:', ja: '🦞 総オブジェクト:', ko: '🦞 총 오브젝트:',
      'zh-CN': '🦞 总物体:', 'zh-TW': '🦞 總物體:',
      hi: '🦞 कुल वस्तुएँ:', 'pt-BR': '🦞 Total de Objetos:', fr: '🦞 Total d\'Objets :'
    },
    'map.last_active': {
      en: '🕐 Last Active:', ja: '🕐 最終活動:', ko: '🕐 최근 활동:',
      'zh-CN': '🕐 最后活跃:', 'zh-TW': '🕐 最後活躍:',
      hi: '🕐 अंतिम सक्रिय:', 'pt-BR': '🕐 Última Atividade:', fr: '🕐 Dernière Activité :'
    },
    'map.loading': {
      en: '🌊 Loading islands...', ja: '🌊 島を読み込み中...', ko: '🌊 섬을 불러오는 중...',
      'zh-CN': '🌊 加载岛屿中...', 'zh-TW': '🌊 載入島嶼中...',
      hi: '🌊 द्वीप लोड हो रहे हैं...', 'pt-BR': '🌊 Carregando ilhas...', fr: '🌊 Chargement des îles...'
    },
    'map.no_islands': {
      en: 'No islands registered yet. Be the first!',
      ja: 'まだ島が登録されていません。最初の一人になりましょう！',
      ko: '아직 등록된 섬이 없습니다. 첫 번째가 되세요!',
      'zh-CN': '还没有注册的岛屿。成为第一个吧！',
      'zh-TW': '還沒有註冊的島嶼。成為第一個吧！',
      hi: 'अभी तक कोई द्वीप पंजीकृत नहीं है। पहले बनें!',
      'pt-BR': 'Nenhuma ilha registrada ainda. Seja o primeiro!',
      fr: 'Aucune île enregistrée pour le moment. Soyez le premier !'
    },
    'map.visit_island': {
      en: '🚢 Visit Island', ja: '🚢 島を訪問', ko: '🚢 섬 방문',
      'zh-CN': '🚢 访问岛屿', 'zh-TW': '🚢 訪問島嶼',
      hi: '🚢 द्वीप पर जाएं', 'pt-BR': '🚢 Visitar Ilha', fr: '🚢 Visiter l\'Île'
    },
    'map.go_build': {
      en: '← Go build your island', ja: '← 島を作りに行く', ko: '← 섬을 만들러 가기',
      'zh-CN': '← 去建造你的岛屿', 'zh-TW': '← 去建造你的島嶼',
      hi: '← अपना द्वीप बनाने जाएं', 'pt-BR': '← Vá construir sua ilha', fr: '← Allez construire votre île'
    },

    // ── Leaderboard tabs ──
    'lb.level': {
      en: '⬆️ Level', ja: '⬆️ レベル', ko: '⬆️ 레벨',
      'zh-CN': '⬆️ 等级', 'zh-TW': '⬆️ 等級',
      hi: '⬆️ स्तर', 'pt-BR': '⬆️ Nível', fr: '⬆️ Niveau'
    },
    'lb.visits': {
      en: '👁 Visits', ja: '👁 訪問', ko: '👁 방문',
      'zh-CN': '👁 访问', 'zh-TW': '👁 訪問',
      hi: '👁 विज़िट', 'pt-BR': '👁 Visitas', fr: '👁 Visites'
    },
    'lb.objects': {
      en: '🧱 Objects', ja: '🧱 オブジェクト', ko: '🧱 오브젝트',
      'zh-CN': '🧱 物体', 'zh-TW': '🧱 物體',
      hi: '🧱 वस्तुएँ', 'pt-BR': '🧱 Objetos', fr: '🧱 Objets'
    },

    // ── World stats panel ──
    'panel.world_stats': {
      en: '📊 World Stats', ja: '📊 ワールド統計', ko: '📊 월드 통계',
      'zh-CN': '📊 世界统计', 'zh-TW': '📊 世界統計',
      hi: '📊 विश्व आँकड़े', 'pt-BR': '📊 Estatísticas do Mundo', fr: '📊 Statistiques Mondiales'
    },
    'panel.help': {
      en: '❓ Help & Shortcuts', ja: '❓ ヘルプ＆ショートカット', ko: '❓ 도움말 & 단축키',
      'zh-CN': '❓ 帮助与快捷键', 'zh-TW': '❓ 幫助與快捷鍵',
      hi: '❓ सहायता और शॉर्टकट', 'pt-BR': '❓ Ajuda & Atalhos', fr: '❓ Aide & Raccourcis'
    },
    'panel.snapshots': {
      en: '📸 Snapshots', ja: '📸 スナップショット', ko: '📸 스냅샷',
      'zh-CN': '📸 快照', 'zh-TW': '📸 快照',
      hi: '📸 स्नैपशॉट', 'pt-BR': '📸 Capturas', fr: '📸 Instantanés'
    },

    // ── Island card labels ──
    'card.my_island': {
      en: '✨ MY ISLAND', ja: '✨ 私の島', ko: '✨ 내 섬',
      'zh-CN': '✨ 我的岛屿', 'zh-TW': '✨ 我的島嶼',
      hi: '✨ मेरा द्वीप', 'pt-BR': '✨ MINHA ILHA', fr: '✨ MON ÎLE'
    },
    'card.new': {
      en: '✨ NEW', ja: '✨ 新着', ko: '✨ 새로운',
      'zh-CN': '✨ 新', 'zh-TW': '✨ 新',
      hi: '✨ नया', 'pt-BR': '✨ NOVO', fr: '✨ NOUVEAU'
    },
    'card.featured': {
      en: '⭐ Featured', ja: '⭐ 注目', ko: '⭐ 추천',
      'zh-CN': '⭐ 精选', 'zh-TW': '⭐ 精選',
      hi: '⭐ विशेष', 'pt-BR': '⭐ Destaque', fr: '⭐ En Vedette'
    },

    // ── Error messages ──
    'error.load_islands': {
      en: '⚠️ Could not load islands.',
      ja: '⚠️ 島を読み込めませんでした。',
      ko: '⚠️ 섬을 불러올 수 없습니다.',
      'zh-CN': '⚠️ 无法加载岛屿。',
      'zh-TW': '⚠️ 無法載入島嶼。',
      hi: '⚠️ द्वीप लोड नहीं हो सके।',
      'pt-BR': '⚠️ Não foi possível carregar as ilhas.',
      fr: '⚠️ Impossible de charger les îles.'
    },
    'error.no_islands_match': {
      en: 'No islands match', ja: '一致する島がありません', ko: '일치하는 섬이 없습니다',
      'zh-CN': '没有匹配的岛屿', 'zh-TW': '沒有匹配的島嶼',
      hi: 'कोई मिलान द्वीप नहीं', 'pt-BR': 'Nenhuma ilha encontrada', fr: 'Aucune île correspondante'
    },
    'error.no_type_islands': {
      en: 'islands found', ja: '島が見つかりました', ko: '섬이 발견되었습니다',
      'zh-CN': '找到岛屿', 'zh-TW': '找到島嶼',
      hi: 'द्वीप मिले', 'pt-BR': 'ilhas encontradas', fr: 'îles trouvées'
    },
    'error.no_islands_yet': {
      en: 'No islands yet. Create the first one! 🏝',
      ja: 'まだ島がありません。最初の島を作りましょう！🏝',
      ko: '아직 섬이 없습니다. 첫 번째 섬을 만들어보세요! 🏝',
      'zh-CN': '还没有岛屿。创建第一个吧！🏝',
      'zh-TW': '還沒有島嶼。建立第一個吧！🏝',
      hi: 'अभी तक कोई द्वीप नहीं। पहला बनाएं! 🏝',
      'pt-BR': 'Nenhuma ilha ainda. Crie a primeira! 🏝',
      fr: 'Pas encore d\'île. Créez la première ! 🏝'
    },

    // ── Misc / common ──
    'common.loading': {
      en: 'Loading...', ja: '読み込み中...', ko: '로딩 중...',
      'zh-CN': '加载中...', 'zh-TW': '載入中...',
      hi: 'लोड हो रहा है...', 'pt-BR': 'Carregando...', fr: 'Chargement...'
    },
    'common.close': {
      en: 'Close', ja: '閉じる', ko: '닫기',
      'zh-CN': '关闭', 'zh-TW': '關閉',
      hi: 'बंद करें', 'pt-BR': 'Fechar', fr: 'Fermer'
    },
    'common.back': {
      en: '← Back', ja: '← 戻る', ko: '← 뒤로',
      'zh-CN': '← 返回', 'zh-TW': '← 返回',
      hi: '← वापस', 'pt-BR': '← Voltar', fr: '← Retour'
    },
    'common.load_more': {
      en: 'Load more islands ↓', ja: 'もっと島を読み込む ↓', ko: '더 많은 섬 불러오기 ↓',
      'zh-CN': '加载更多岛屿 ↓', 'zh-TW': '載入更多島嶼 ↓',
      hi: 'और द्वीप लोड करें ↓', 'pt-BR': 'Carregar mais ilhas ↓', fr: 'Charger plus d\'îles ↓'
    },
    'common.sailing_to': {
      en: 'Sailing to', ja: '航海中', ko: '항해 중',
      'zh-CN': '正在航向', 'zh-TW': '正在航向',
      hi: 'की ओर जा रहे हैं', 'pt-BR': 'Navegando para', fr: 'Navigation vers'
    },

    // ── Language names for the switcher ──
    'lang.en': { en: 'English', ja: 'English', ko: 'English', 'zh-CN': 'English', 'zh-TW': 'English', hi: 'English', 'pt-BR': 'English', fr: 'English' },
    'lang.ja': { en: '日本語', ja: '日本語', ko: '日本語', 'zh-CN': '日本語', 'zh-TW': '日本語', hi: '日本語', 'pt-BR': '日本語', fr: '日本語' },
    'lang.ko': { en: '한국어', ja: '한국어', ko: '한국어', 'zh-CN': '한국어', 'zh-TW': '한국어', hi: '한국어', 'pt-BR': '한국어', fr: '한국어' },
    'lang.zh-CN': { en: '简体中文', ja: '简体中文', ko: '简体中文', 'zh-CN': '简体中文', 'zh-TW': '简体中文', hi: '简体中文', 'pt-BR': '简体中文', fr: '简体中文' },
    'lang.zh-TW': { en: '繁體中文', ja: '繁體中文', ko: '繁體中文', 'zh-CN': '繁體中文', 'zh-TW': '繁體中文', hi: '繁體中文', 'pt-BR': '繁體中文', fr: '繁體中文' },
    'lang.hi': { en: 'हिन्दी', ja: 'हिन्दी', ko: 'हिन्दी', 'zh-CN': 'हिन्दी', 'zh-TW': 'हिन्दी', hi: 'हिन्दी', 'pt-BR': 'हिन्दी', fr: 'हिन्दी' },
    'lang.pt-BR': { en: 'Português', ja: 'Português', ko: 'Português', 'zh-CN': 'Português', 'zh-TW': 'Português', hi: 'Português', 'pt-BR': 'Português', fr: 'Português' },
    'lang.fr': { en: 'Français', ja: 'Français', ko: 'Français', 'zh-CN': 'Français', 'zh-TW': 'Français', hi: 'Français', 'pt-BR': 'Français', fr: 'Français' },
  };

  // ── Detect language ──
  function detectLang() {
    // 1. Check localStorage
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGS.includes(stored)) return stored;

    // 2. Check navigator.language
    const nav = (navigator.language || navigator.userLanguage || '').trim();
    // Exact match first
    if (SUPPORTED_LANGS.includes(nav)) return nav;
    // zh-Hans → zh-CN, zh-Hant → zh-TW
    if (/^zh[-_](Hans|CN|SG)/i.test(nav)) return 'zh-CN';
    if (/^zh[-_](Hant|TW|HK|MO)/i.test(nav)) return 'zh-TW';
    if (/^zh/i.test(nav)) return 'zh-CN';
    // pt-BR
    if (/^pt[-_]BR/i.test(nav)) return 'pt-BR';
    if (/^pt/i.test(nav)) return 'pt-BR';
    // Base language match
    const base = nav.split(/[-_]/)[0].toLowerCase();
    const match = SUPPORTED_LANGS.find(l => l.split(/[-_]/)[0].toLowerCase() === base);
    if (match) return match;

    return DEFAULT_LANG;
  }

  let currentLang = detectLang();

  // ── Core API ──
  function t(key) {
    const entry = translations[key];
    if (!entry) return key;
    return entry[currentLang] || entry[DEFAULT_LANG] || key;
  }

  function setLang(code) {
    if (!SUPPORTED_LANGS.includes(code)) return;
    currentLang = code;
    localStorage.setItem(STORAGE_KEY, code);
    document.documentElement.lang = code === 'zh-CN' ? 'zh-Hans' : code === 'zh-TW' ? 'zh-Hant' : code;
    applyI18n();
    // Dispatch event so page-specific JS can react
    window.dispatchEvent(new CustomEvent('langchange', { detail: { lang: code } }));
  }

  function getLang() {
    return currentLang;
  }

  function getSupportedLangs() {
    return SUPPORTED_LANGS.slice();
  }

  // ── Apply translations to data-i18n elements ──
  function applyI18n() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translated = t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = translated;
      } else {
        el.textContent = translated;
      }
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
    });
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
  }

  // ── Language Switcher Widget ──
  function createLangSwitcher(containerSelector) {
    const container = containerSelector
      ? document.querySelector(containerSelector)
      : null;

    const wrapper = document.createElement('div');
    wrapper.id = 'lang-switcher';
    wrapper.style.cssText = 'position:relative;display:inline-block;z-index:999;';

    const btn = document.createElement('button');
    btn.id = 'lang-switcher-btn';
    btn.textContent = '🌐';
    btn.title = 'Language';
    btn.style.cssText = 'font-size:14px;background:rgba(20,50,80,0.6);border:1px solid rgba(100,180,255,0.3);color:#88ccff;border-radius:8px;padding:4px 10px;cursor:pointer;transition:all .2s;line-height:1.2;min-width:36px;text-align:center;';
    btn.onmouseenter = function() { btn.style.background = 'rgba(30,70,110,0.8)'; btn.style.borderColor = 'rgba(100,180,255,0.6)'; };
    btn.onmouseleave = function() { if (!dropdown.style.display || dropdown.style.display === 'none') { btn.style.background = 'rgba(20,50,80,0.6)'; btn.style.borderColor = 'rgba(100,180,255,0.3)'; } };

    const dropdown = document.createElement('div');
    dropdown.id = 'lang-dropdown';
    dropdown.style.cssText = 'display:none;position:absolute;top:calc(100% + 4px);right:0;background:rgba(6,14,26,0.97);border:1px solid rgba(100,180,255,0.25);border-radius:10px;padding:4px;min-width:140px;box-shadow:0 8px 32px rgba(0,0,0,0.7);backdrop-filter:blur(12px);z-index:1000;';

    SUPPORTED_LANGS.forEach(code => {
      const item = document.createElement('button');
      item.style.cssText = 'display:block;width:100%;text-align:left;padding:7px 12px;font-size:13px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:none;border:none;color:#c8dce8;cursor:pointer;border-radius:6px;transition:background .15s;white-space:nowrap;';
      item.textContent = t('lang.' + code);
      if (code === currentLang) {
        item.style.background = 'rgba(100,180,255,0.15)';
        item.style.color = '#7cc8ff';
        item.style.fontWeight = '600';
      }
      item.onmouseenter = function() { item.style.background = 'rgba(100,180,255,0.12)'; };
      item.onmouseleave = function() { item.style.background = code === currentLang ? 'rgba(100,180,255,0.15)' : 'none'; };
      item.onclick = function(e) {
        e.stopPropagation();
        setLang(code);
        dropdown.style.display = 'none';
        btn.style.background = 'rgba(20,50,80,0.6)';
        btn.style.borderColor = 'rgba(100,180,255,0.3)';
        // Rebuild dropdown highlights
        rebuildDropdown();
      };
      dropdown.appendChild(item);
    });

    function rebuildDropdown() {
      dropdown.innerHTML = '';
      SUPPORTED_LANGS.forEach(code => {
        const item = document.createElement('button');
        item.style.cssText = 'display:block;width:100%;text-align:left;padding:7px 12px;font-size:13px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:none;border:none;color:#c8dce8;cursor:pointer;border-radius:6px;transition:background .15s;white-space:nowrap;';
        item.textContent = t('lang.' + code);
        if (code === currentLang) {
          item.style.background = 'rgba(100,180,255,0.15)';
          item.style.color = '#7cc8ff';
          item.style.fontWeight = '600';
        }
        item.onmouseenter = function() { item.style.background = 'rgba(100,180,255,0.12)'; };
        item.onmouseleave = function() { item.style.background = code === currentLang ? 'rgba(100,180,255,0.15)' : 'none'; };
        item.onclick = function(e) {
          e.stopPropagation();
          setLang(code);
          dropdown.style.display = 'none';
          rebuildDropdown();
        };
        dropdown.appendChild(item);
      });
    }

    btn.onclick = function(e) {
      e.stopPropagation();
      const visible = dropdown.style.display !== 'none';
      dropdown.style.display = visible ? 'none' : 'block';
    };

    // Close dropdown on outside click
    document.addEventListener('click', function() {
      dropdown.style.display = 'none';
    });

    wrapper.appendChild(btn);
    wrapper.appendChild(dropdown);

    if (container) {
      container.appendChild(wrapper);
    }

    return wrapper;
  }

  // ── Dynamic content translations (for JS-generated text) ──
  const dynKeys = {
    'card.visit': { en:'Visit →', ja:'訪問 →', ko:'방문 →', 'zh-CN':'访问 →', 'zh-TW':'造訪 →', hi:'भ्रमण →', 'pt-BR':'Visitar →', fr:'Visiter →' },
    'card.by': { en:'by', ja:'作者', ko:'만든이', 'zh-CN':'作者', 'zh-TW':'作者', hi:'द्वारा', 'pt-BR':'por', fr:'par' },
    'card.items': { en:'items', ja:'アイテム', ko:'아이템', 'zh-CN':'物品', 'zh-TW':'物品', hi:'आइटम', 'pt-BR':'itens', fr:'objets' },
    'card.visits': { en:'visits', ja:'訪問', ko:'방문', 'zh-CN':'访问', 'zh-TW':'造訪', hi:'यात्रा', 'pt-BR':'visitas', fr:'visites' },
    'card.visit_singular': { en:'visit', ja:'訪問', ko:'방문', 'zh-CN':'访问', 'zh-TW':'造訪', hi:'यात्रा', 'pt-BR':'visita', fr:'visite' },
    'card.created_ago': { en:'Created', ja:'作成', ko:'생성', 'zh-CN':'创建于', 'zh-TW':'建立於', hi:'बनाया', 'pt-BR':'Criado', fr:'Créé' },
    'card.ago': { en:'ago', ja:'前', ko:'전', 'zh-CN':'前', 'zh-TW':'前', hi:'पहले', 'pt-BR':'atrás', fr:'il y a' },
    'card.most_visited': { en:'🏆 Most Visited', ja:'🏆 最多訪問', ko:'🏆 가장 많이 방문', 'zh-CN':'🏆 最多访问', 'zh-TW':'🏆 最多造訪', hi:'🏆 सबसे अधिक देखा गया', 'pt-BR':'🏆 Mais Visitado', fr:'🏆 Plus Visité' },
    'card.highest_level': { en:'⭐ Highest Level', ja:'⭐ 最高レベル', ko:'⭐ 최고 레벨', 'zh-CN':'⭐ 最高等级', 'zh-TW':'⭐ 最高等級', hi:'⭐ उच्चतम स्तर', 'pt-BR':'⭐ Nível Mais Alto', fr:'⭐ Niveau le Plus Élevé' },
    'card.most_built': { en:'🏗️ Most Built', ja:'🏗️ 最多建設', ko:'🏗️ 가장 많이 건설', 'zh-CN':'🏗️ 建设最多', 'zh-TW':'🏗️ 建設最多', hi:'🏗️ सबसे अधिक निर्मित', 'pt-BR':'🏗️ Mais Construído', fr:'🏗️ Plus Construit' },
    'type.farm.desc': { en:'Grow crops & raise animals', ja:'作物を育て動物を飼う', ko:'작물 재배 & 동물 사육', 'zh-CN':'种植作物和饲养动物', 'zh-TW':'種植作物和飼養動物', hi:'फसल उगाएं और पशु पालें', 'pt-BR':'Cultive e crie animais', fr:'Cultivez et élevez des animaux' },
    'type.fish.desc': { en:'Fish & explore the sea', ja:'釣りと海の探索', ko:'낚시 & 바다 탐험', 'zh-CN':'钓鱼和探索大海', 'zh-TW':'釣魚和探索大海', hi:'मछली पकड़ें और समुद्र का अन्वेषण करें', 'pt-BR':'Pesque e explore o mar', fr:'Pêchez et explorez la mer' },
    'type.mine.desc': { en:'Mine ores & forge tools', ja:'鉱石を掘り道具を作る', ko:'광석 채굴 & 도구 제작', 'zh-CN':'采矿和锻造工具', 'zh-TW':'採礦和鍛造工具', hi:'अयस्क खोदें और उपकरण बनाएं', 'pt-BR':'Minere e forje ferramentas', fr:'Minez et forgez des outils' },
    'type.forest.desc': { en:'Chop wood & build treehouses', ja:'木を切ってツリーハウスを建てる', ko:'나무 베기 & 트리하우스 건설', 'zh-CN':'伐木和建造树屋', 'zh-TW':'伐木和建造樹屋', hi:'लकड़ी काटें और ट्रीहाउस बनाएं', 'pt-BR':'Corte madeira e construa casas na árvore', fr:'Coupez du bois et construisez des cabanes' },
    'bio.thriving_farm': { en:'A thriving farm island with {n} items. Worth a visit!', ja:'{n}個のアイテムがある活気ある農場島。訪問の価値あり！', ko:'{n}개 아이템이 있는 번성하는 농장 섬. 방문할 가치가 있습니다!', 'zh-CN':'一个繁荣的农场岛，有{n}个物品。值得一看！', 'zh-TW':'一個繁榮的農場島，有{n}個物品。值得一看！', hi:'{n} आइटम वाला एक समृद्ध खेत द्वीप। देखने लायक!', 'pt-BR':'Uma ilha fazenda próspera com {n} itens. Vale a visita!', fr:'Une île ferme prospère avec {n} objets. À visiter !' },
    'bio.cozy_farm': { en:'A cozy farm island with {n} items to discover.', ja:'{n}個のアイテムがある居心地のいい農場島。', ko:'{n}개 아이템이 있는 아늑한 농장 섬.', 'zh-CN':'一个温馨的农场岛，有{n}个物品等你发现。', 'zh-TW':'一個溫馨的農場島，有{n}個物品等你發現。', hi:'{n} आइटम वाला एक आरामदायक खेत द्वीप।', 'pt-BR':'Uma aconchegante ilha fazenda com {n} itens para descobrir.', fr:'Une île ferme chaleureuse avec {n} objets à découvrir.' },
    'bio.young_island': { en:'A young {type} island with {n} items placed so far.', ja:'まだ若い{type}島、{n}個のアイテム配置済み。', ko:'{n}개 아이템이 있는 젊은 {type} 섬.', 'zh-CN':'一个年轻的{type}岛，已放置{n}个物品。', 'zh-TW':'一個年輕的{type}島，已放置{n}個物品。', hi:'{n} आइटम वाला एक युवा {type} द्वीप।', 'pt-BR':'Uma jovem ilha {type} com {n} itens colocados.', fr:'Une jeune île {type} avec {n} objets placés.' },
    'bio.taking_shape': { en:'This {type} island is taking shape — {n} items and counting.', ja:'この{type}島は形になりつつある — {n}個のアイテム。', ko:'이 {type} 섬이 형태를 갖추고 있습니다 — {n}개 아이템.', 'zh-CN':'这个{type}岛正在成形 — {n}个物品并在增长。', 'zh-TW':'這個{type}島正在成形 — {n}個物品並在增長。', hi:'यह {type} द्वीप आकार ले रहा है — {n} आइटम।', 'pt-BR':'Esta ilha {type} está tomando forma — {n} itens e contando.', fr:'Cette île {type} prend forme — {n} objets et ça continue.' },
    'bio.explore': { en:'Explore this {type} island! {n} items await.', ja:'この{type}島を探索しよう！{n}個のアイテムが待っている。', ko:'이 {type} 섬을 탐험하세요! {n}개 아이템이 기다립니다.', 'zh-CN':'探索这个{type}岛！{n}个物品等着你。', 'zh-TW':'探索這個{type}島！{n}個物品等著你。', hi:'इस {type} द्वीप का अन्वेषण करें! {n} आइटम इंतज़ार कर रहे हैं।', 'pt-BR':'Explore esta ilha {type}! {n} itens aguardam.', fr:'Explorez cette île {type} ! {n} objets vous attendent.' },
    'bio.well_developed': { en:'A well-developed {type} island — {n} items placed and more to come.', ja:'よく開発された{type}島 — {n}個のアイテム配置済み。', ko:'잘 개발된 {type} 섬 — {n}개 아이템이 있습니다.', 'zh-CN':'一个发展良好的{type}岛 — 已放置{n}个物品。', 'zh-TW':'一個發展良好的{type}島 — 已放置{n}個物品。', hi:'एक अच्छी तरह से विकसित {type} द्वीप — {n} आइटम।', 'pt-BR':'Uma ilha {type} bem desenvolvida — {n} itens colocados.', fr:'Une île {type} bien développée — {n} objets placés.' },
    'time.just_now': { en:'just now', ja:'たった今', ko:'방금', 'zh-CN':'刚刚', 'zh-TW':'剛剛', hi:'अभी', 'pt-BR':'agora', fr:'à l\'instant' },
    'time.minutes': { en:'{n}m ago', ja:'{n}分前', ko:'{n}분 전', 'zh-CN':'{n}分钟前', 'zh-TW':'{n}分鐘前', hi:'{n}मिनट पहले', 'pt-BR':'{n}min atrás', fr:'il y a {n}min' },
    'time.hours': { en:'{n}h ago', ja:'{n}時間前', ko:'{n}시간 전', 'zh-CN':'{n}小时前', 'zh-TW':'{n}小時前', hi:'{n}घंटे पहले', 'pt-BR':'{n}h atrás', fr:'il y a {n}h' },
    'time.days': { en:'{n}d ago', ja:'{n}日前', ko:'{n}일 전', 'zh-CN':'{n}天前', 'zh-TW':'{n}天前', hi:'{n}दिन पहले', 'pt-BR':'{n}d atrás', fr:'il y a {n}j' },
    'stats.islands': { en:'islands', ja:'島', ko:'섬', 'zh-CN':'岛屿', 'zh-TW':'島嶼', hi:'द्वीप', 'pt-BR':'ilhas', fr:'îles' },
    'stats.total_visits': { en:'total visits', ja:'総訪問数', ko:'총 방문', 'zh-CN':'总访问', 'zh-TW':'總造訪', hi:'कुल यात्रा', 'pt-BR':'visitas totais', fr:'visites totales' },
    'stats.farms': { en:'farms', ja:'農場', ko:'농장', 'zh-CN':'农场', 'zh-TW':'農場', hi:'खेत', 'pt-BR':'fazendas', fr:'fermes' },
    'stats.fisheries': { en:'fisheries', ja:'漁場', ko:'어장', 'zh-CN':'渔场', 'zh-TW':'漁場', hi:'मत्स्य', 'pt-BR':'pesqueiros', fr:'pêcheries' },
    'stats.mines': { en:'mines', ja:'鉱山', ko:'광산', 'zh-CN':'矿山', 'zh-TW':'礦山', hi:'खदान', 'pt-BR':'minas', fr:'mines' },
    'stats.forests': { en:'forests', ja:'森', ko:'숲', 'zh-CN':'森林', 'zh-TW':'森林', hi:'वन', 'pt-BR':'florestas', fr:'forêts' },
    'stats.online': { en:'online', ja:'オンライン', ko:'온라인', 'zh-CN':'在线', 'zh-TW':'在線', hi:'ऑनलाइन', 'pt-BR':'online', fr:'en ligne' },
    'lobby.load_more': { en:'Load {n} more islands ↓', ja:'さらに{n}島を読み込む ↓', ko:'{n}개 더 불러오기 ↓', 'zh-CN':'加载更多{n}个岛屿 ↓', 'zh-TW':'載入更多{n}個島嶼 ↓', hi:'{n} और द्वीप लोड करें ↓', 'pt-BR':'Carregar mais {n} ilhas ↓', fr:'Charger {n} îles de plus ↓' },
    'lobby.end': { en:"You've explored all islands!", ja:'すべての島を探索しました！', ko:'모든 섬을 탐험했습니다!', 'zh-CN':'你已经探索了所有岛屿！', 'zh-TW':'你已經探索了所有島嶼！', hi:'आपने सभी द्वीपों का अन्वेषण किया!', 'pt-BR':'Você explorou todas as ilhas!', fr:'Vous avez exploré toutes les îles !' },
    'island.new': { en:'✨ NEW', ja:'✨ 新着', ko:'✨ 새로운', 'zh-CN':'✨ 新岛', 'zh-TW':'✨ 新島', hi:'✨ नया', 'pt-BR':'✨ NOVO', fr:'✨ NOUVEAU' },
    // ── Push Notifications ──
    'push.banner': { en:'🔔 Get notified when someone visits or raids your island?', ja:'🔔 誰かがあなたの島を訪問したり襲撃した時に通知を受け取りますか？', ko:'🔔 누군가 당신의 섬을 방문하거나 습격하면 알림을 받으시겠습니까?', 'zh-CN':'🔔 有人访问或袭击你的岛屿时接收通知？', 'zh-TW':'🔔 有人造訪或襲擊你的島嶼時接收通知？', hi:'🔔 जब कोई आपके द्वीप पर आए या हमला करे तो सूचना पाएं?', 'pt-BR':'🔔 Receba notificações quando alguém visitar ou atacar sua ilha?', fr:'🔔 Être notifié quand quelqu\'un visite ou attaque votre île ?' },
    'push.enable': { en:'Enable', ja:'有効にする', ko:'활성화', 'zh-CN':'开启', 'zh-TW':'開啟', hi:'सक्षम करें', 'pt-BR':'Ativar', fr:'Activer' },
    'push.raid_title': { en:'🔥 Your island was raided!', ja:'🔥 あなたの島が襲撃されました！', ko:'🔥 당신의 섬이 습격당했습니다!', 'zh-CN':'🔥 你的岛屿被袭击了！', 'zh-TW':'🔥 你的島嶼被襲擊了！', hi:'🔥 आपके द्वीप पर हमला हुआ!', 'pt-BR':'🔥 Sua ilha foi atacada!', fr:'🔥 Votre île a été attaquée !' },
    'push.bomb_title': { en:'💣 Your island was bombed!', ja:'💣 あなたの島が爆撃されました！', ko:'💣 당신의 섬이 폭격당했습니다!', 'zh-CN':'💣 你的岛屿被炸了！', 'zh-TW':'💣 你的島嶼被炸了！', hi:'💣 आपके द्वीप पर बम गिरा!', 'pt-BR':'💣 Sua ilha foi bombardeada!', fr:'💣 Votre île a été bombardée !' },
    'push.guestbook_title': { en:'📝 New guestbook message!', ja:'📝 新しいゲストブックメッセージ！', ko:'📝 새 방명록 메시지!', 'zh-CN':'📝 新留言！', 'zh-TW':'📝 新留言！', hi:'📝 नया गेस्टबुक संदेश!', 'pt-BR':'📝 Nova mensagem no livro de visitas!', fr:'📝 Nouveau message dans le livre d\'or !' },
    'push.gift_title': { en:'🎁 You received a gift!', ja:'🎁 ギフトを受け取りました！', ko:'🎁 선물을 받았습니다!', 'zh-CN':'🎁 你收到了礼物！', 'zh-TW':'🎁 你收到了禮物！', hi:'🎁 आपको उपहार मिला!', 'pt-BR':'🎁 Você recebeu um presente!', fr:'🎁 Vous avez reçu un cadeau !' },
  };
  // Merge dynamic keys into main translations
  Object.assign(translations, dynKeys);

  // ── Helper: translate with interpolation ──
  window.ti = function(key, vars) {
    let s = t(key);
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), v);
      }
    }
    return s;
  };

  // ── Expose globals ──
  window.t = t;
  window.setLang = setLang;
  window.getLang = getLang;
  window.getSupportedLangs = getSupportedLangs;
  window.applyI18n = applyI18n;
  window.createLangSwitcher = createLangSwitcher;
  window.CLAWVERSE_I18N = { t, setLang, getLang, getSupportedLangs, applyI18n, createLangSwitcher, translations };

  // Auto-apply on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { applyI18n(); });
  } else {
    applyI18n();
  }
})();
