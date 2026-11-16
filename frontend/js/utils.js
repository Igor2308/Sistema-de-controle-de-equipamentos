/* Constantes compartilhadas pelas telas (importadas como módulo ES).
   Exemplo de uso:  import { URL_LOGIN } from "./utils.js";  */

// Endereço da API (FastAPI). As páginas rodam em outro servidor (Live Server, porta 5500),
// então toda chamada à API usa este endereço completo. É o único lugar para trocar a porta.
export const API_BASE = "http://127.0.0.1:8000";

export const URL_LOGIN = API_BASE + "/auth/login";
