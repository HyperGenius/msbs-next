import React, { createContext, useContext } from 'react';

// 認証状態を保持するコンテキスト
const ClerkMockContext = createContext<{ user: any } | null>(null);

// モック用の Provider
// StorybookのDecoratorからユーザー情報を受け取ります
export const ClerkProvider = ({ children, user }: { children: React.ReactNode; user?: any }) => {
  return (
    <ClerkMockContext.Provider value={user ? { user } : null}>
      {children}
    </ClerkMockContext.Provider>
  );
};

// --- 以下、Clerkコンポーネント/フックのモック ---

export const SignedIn = ({ children }: { children: React.ReactNode }) => {
  const context = useContext(ClerkMockContext);
  return context?.user ? <>{children}</> : null;
};

export const SignedOut = ({ children }: { children: React.ReactNode }) => {
  const context = useContext(ClerkMockContext);
  return !context?.user ? <>{children}</> : null;
};

export const UserButton = () => {
  const context = useContext(ClerkMockContext);
  const imageUrl = context?.user?.imageUrl;
  
  return (
    <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-white bg-gray-700">
      {imageUrl ? (
        <img src={imageUrl} alt="User" className="w-full h-full object-cover" />
      ) : (
        <div className="flex items-center justify-center w-full h-full text-xs font-bold text-white">
          U
        </div>
      )}
    </div>
  );
};

export const SignInButton = ({ children }: { children: React.ReactNode }) => {
  return <button onClick={() => alert("Sign In Clicked (Storybook Mock)")}>{children}</button>;
};

export const useUser = () => {
  const context = useContext(ClerkMockContext);
  return {
    user: context?.user || null,
    isLoaded: true,
    isSignedIn: !!context?.user,
  };
};

export const useAuth = () => {
  const context = useContext(ClerkMockContext);
  return {
    isLoaded: true,
    isSignedIn: !!context?.user,
    userId: context?.user?.id,
    getToken: () => Promise.resolve('mock-token'),
    signOut: () => Promise.resolve(),
  };
};
