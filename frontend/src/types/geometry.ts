/** 3次元ベクトル座標（位置・速度スナップショットなどで使用） */
export interface Vector3 {
    x: number;
    y: number;
    z: number;
}

/** バトルフィールド上の障害物（円柱形） */
export interface Obstacle {
    obstacle_id: string;
    position: { x: number; y: number; z: number };
    radius: number;
    height: number;
}
