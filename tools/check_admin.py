import pymysql

def check_admin():
    # 连接数据库
    conn = pymysql.connect(
        host='localhost',
        user='pdf123',
        password='p2kfbbBLaTtxj6S3',
        database='pdf123'
    )
    
    try:
        with conn.cursor() as cursor:
            # 查询管理员信息
            cursor.execute("SELECT username, password, status FROM admin WHERE username = 'admin'")
            result = cursor.fetchone()
            
            if result:
                print(f"管理员信息:")
                print(f"用户名: {result[0]}")
                print(f"密码: {result[1]}")
                print(f"状态: {'启用' if result[2] == 1 else '禁用'}")
                print(f"是否为加密密码: {'是' if result[1].startswith('pbkdf2:sha256:') else '否'}")
            else:
                print("未找到管理员账号")
    finally:
        conn.close()

if __name__ == '__main__':
    check_admin() 