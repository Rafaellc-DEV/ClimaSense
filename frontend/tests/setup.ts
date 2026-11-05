import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// As telas carregam sob demanda e a suíte roda arquivos em paralelo: com a máquina ocupada, o prazo padrão de
// 1 s das esperas (findBy*, waitFor) dá falso negativo. Só o prazo muda; nenhuma asserção é afrouxada.
configure({ asyncUtilTimeout: 5000 });
