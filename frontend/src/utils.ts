import { jwtDecode } from 'jwt-decode'; 

const isTokenExpired = (token: string): boolean => {
    if (!token) return true;
    const decoded: any = jwtDecode(token);
    const now = Date.now() / 1000;
    return decoded.exp < now;
};

export default isTokenExpired;
