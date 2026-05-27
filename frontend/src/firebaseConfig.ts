import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";

const firebaseConfig = {
    apiKey: "AIzaSyC7NzXqS6WYtH5tomGZzCP7x_qN46f9lWk",
    authDomain: "riversentinel-ae0b0.firebaseapp.com",
    databaseURL: "https://riversentinel-ae0b0-default-rtdb.asia-southeast1.firebasedatabase.app",
    projectId: "riversentinel-ae0b0",
    storageBucket: "riversentinel-ae0b0.firebasestorage.app",
    messagingSenderId: "934027743275",
    appId: "1:934027743275:web:041be49bcd94e544f7da6e",
    measurementId: "G-ZDP0VGXLJK"
};

const app = initializeApp(firebaseConfig);
export const db = getDatabase(app);
