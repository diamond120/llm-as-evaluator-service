import { useContext } from "react";
import { AuthContext } from "../components/AuthContext";

export const useAuth = () => {
    return useContext(AuthContext);
};
