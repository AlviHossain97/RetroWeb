import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "retroweb.language";

export type Lang = "en" | "es" | "fr" | "de" | "ja" | "pt";

const TRANSLATIONS: Record<Lang, Record<string, string>> = {
  en: {
    "nav.home": "Home",
    "nav.library": "Library",
    "nav.settings": "Settings",
    "nav.chat": "Chat",
    "nav.controller": "Controller",
    "nav.saves": "Saves",
    "home.welcome": "Welcome to RetroWeb",
    "home.continue": "Continue Playing",
    "library.search": "Search library...",
    "library.upload": "Upload ROM",
    "library.empty": "No games in your library yet",
    "library.addToLibrary": "Add to Library",
    "library.memoryOnly": "Memory Only",
    "library.fetchArt": "Fetch Art",
    "settings.title": "Settings",
    "settings.reset": "Reset",
    "settings.display": "Display",
    "settings.audio": "Audio",
    "settings.input": "Input",
    "settings.saves": "Saves",
    "settings.data": "Data Management",
    "settings.accessibility": "Accessibility",
    "settings.about": "About & Debug",
    "chat.askAnything": "Ask me anything",
    "chat.recommend": "Recommend",
    "chat.walkthrough": "Walkthrough",
    "chat.export": "Export",
    "chat.clear": "Clear chat",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.delete": "Delete",
    "common.close": "Close",
    "common.back": "Back",
    "common.next": "Next",
    "common.play": "Play",
    "common.favorite": "Favorite",
  },
  es: {
    "nav.home": "Inicio",
    "nav.library": "Biblioteca",
    "nav.settings": "Ajustes",
    "nav.chat": "Chat",
    "nav.controller": "Mando",
    "nav.saves": "Guardados",
    "home.welcome": "Bienvenido a RetroWeb",
    "home.continue": "Seguir jugando",
    "library.search": "Buscar en biblioteca...",
    "library.upload": "Subir ROM",
    "library.empty": "No hay juegos en tu biblioteca",
    "library.addToLibrary": "Añadir a biblioteca",
    "library.memoryOnly": "Solo memoria",
    "library.fetchArt": "Obtener arte",
    "settings.title": "Ajustes",
    "settings.reset": "Restablecer",
    "common.cancel": "Cancelar",
    "common.save": "Guardar",
    "common.delete": "Eliminar",
    "common.close": "Cerrar",
    "common.back": "Atrás",
    "common.next": "Siguiente",
    "common.play": "Jugar",
    "common.favorite": "Favorito",
    "chat.askAnything": "Pregúntame lo que quieras",
    "chat.recommend": "Recomendar",
    "chat.walkthrough": "Guía",
    "chat.export": "Exportar",
    "chat.clear": "Borrar chat",
  },
  fr: {
    "nav.home": "Accueil",
    "nav.library": "Bibliothèque",
    "nav.settings": "Paramètres",
    "nav.chat": "Discussion",
    "nav.controller": "Manette",
    "nav.saves": "Sauvegardes",
    "home.welcome": "Bienvenue sur RetroWeb",
    "home.continue": "Continuer à jouer",
    "library.search": "Rechercher...",
    "library.upload": "Charger ROM",
    "library.empty": "Aucun jeu dans votre bibliothèque",
    "common.cancel": "Annuler",
    "common.save": "Sauvegarder",
    "common.delete": "Supprimer",
    "common.play": "Jouer",
    "common.favorite": "Favori",
    "chat.askAnything": "Demandez-moi n'importe quoi",
  },
  de: {
    "nav.home": "Startseite",
    "nav.library": "Bibliothek",
    "nav.settings": "Einstellungen",
    "nav.chat": "Chat",
    "nav.controller": "Controller",
    "nav.saves": "Spielstände",
    "home.welcome": "Willkommen bei RetroWeb",
    "home.continue": "Weiterspielen",
    "library.search": "Bibliothek durchsuchen...",
    "library.empty": "Keine Spiele in deiner Bibliothek",
    "common.cancel": "Abbrechen",
    "common.save": "Speichern",
    "common.delete": "Löschen",
    "common.play": "Spielen",
    "chat.askAnything": "Frag mich was",
  },
  ja: {
    "nav.home": "ホーム",
    "nav.library": "ライブラリ",
    "nav.settings": "設定",
    "nav.chat": "チャット",
    "nav.controller": "コントローラー",
    "nav.saves": "セーブ",
    "home.welcome": "RetroWebへようこそ",
    "home.continue": "続きを遊ぶ",
    "library.search": "ライブラリを検索...",
    "library.empty": "ライブラリにゲームがありません",
    "common.cancel": "キャンセル",
    "common.save": "保存",
    "common.delete": "削除",
    "common.play": "プレイ",
    "chat.askAnything": "何でも聞いてください",
  },
  pt: {
    "nav.home": "Início",
    "nav.library": "Biblioteca",
    "nav.settings": "Configurações",
    "nav.chat": "Chat",
    "nav.controller": "Controle",
    "nav.saves": "Saves",
    "home.welcome": "Bem-vindo ao RetroWeb",
    "home.continue": "Continuar jogando",
    "library.search": "Pesquisar biblioteca...",
    "library.empty": "Nenhum jogo na sua biblioteca",
    "common.cancel": "Cancelar",
    "common.save": "Salvar",
    "common.delete": "Excluir",
    "common.play": "Jogar",
    "chat.askAnything": "Pergunte-me qualquer coisa",
  },
};

export const LANGUAGE_LABELS: Record<Lang, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  ja: "日本語",
  pt: "Português",
};

function getStoredLang(): Lang {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored in TRANSLATIONS) return stored as Lang;
  const browser = navigator.language.slice(0, 2);
  if (browser in TRANSLATIONS) return browser as Lang;
  return "en";
}

export function t(key: string, lang?: Lang): string {
  const l = lang ?? getStoredLang();
  return TRANSLATIONS[l]?.[key] ?? TRANSLATIONS.en[key] ?? key;
}

export function useI18n() {
  const [lang, setLangState] = useState<Lang>(getStoredLang);

  useEffect(() => {
    const handler = () => setLangState(getStoredLang());
    window.addEventListener("retroweb:langchange", handler);
    return () => window.removeEventListener("retroweb:langchange", handler);
  }, []);

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(STORAGE_KEY, l);
    setLangState(l);
    window.dispatchEvent(new Event("retroweb:langchange"));
  }, []);

  const translate = useCallback((key: string) => t(key, lang), [lang]);

  return { lang, setLang, t: translate };
}
