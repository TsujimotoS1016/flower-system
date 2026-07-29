import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBPsVIbTqnYG7yRGdby9Hk_5ngvxMDLxUE",
  authDomain: "bento-inventory-app.firebaseapp.com",
  projectId: "bento-inventory-app",
  storageBucket: "bento-inventory-app.firebasestorage.app",
  messagingSenderId: "698485599279",
  appId: "1:698485599279:web:d38793f3244b8c7f396ada"
};

export const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);
